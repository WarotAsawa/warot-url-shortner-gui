import streamlit as st 
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.hasher import Hasher
import boto3
from botocore.exceptions import ClientError
import yaml
from yaml.loader import SafeLoader
import qrcode
import qrcode.image.svg
import os
from time import sleep


# Get Config from config.yaml
with open('./config/config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)
qrBucketName = config['qrBucketName']
qrBucketPrefix = config['qrBucketPrefix']
shortDomainName = config['shortDomainName']
region = config['region']
tableName = config['tableName']
st.session_state['allURL'] = []
st.session_state['newURL'] = ''
st.session_state['newRedirect'] = ''
st.set_page_config(page_title="WAROT SHORTENNER")

def PutObjectToS3(itemName, bucketName , S3Path, ContentType):
    s3 = boto3.client('s3')
    if ContentType is None:
        ContentType = 'application/octet-stream'
    try:
        print("Uploading File Name:",itemName, " To Bucket Name : ", bucketName, " with path : ", S3Path, " ContentType : ", ContentType)
        response = s3.upload_file(itemName, bucketName, S3Path, ExtraArgs={'ContentType': ContentType})
    except ClientError as e:
        print(e)
        return False
    return True

def GetObjectFromS3(itemName, bucketName, S3Path):
    s3 = boto3.client('s3')
    try:
        print("Downling File Name:",itemName, " To Bucket Name : ", bucketName, " with path : ", S3Path)
        s3.download_file(bucketName, S3Path, itemName)
    except ClientError as e:
        print(e)
        return None
    return True

def GeneratePresignedURL(bucketName, S3Path, expiration=3600):
    s3 = boto3.client('s3')
    try:
        print("Generate Presigned URL for Bucket Name : ", bucketName, " with path : ", S3Path)
        response = s3.generate_presigned_url('get_object', Params={'Bucket': bucketName, 'Key': S3Path}, ExpiresIn=expiration)
    except ClientError as e:
        print(e)
        return False
    print(response)
    return response
# Gen SVG QR Code
def CreateQRSVG(url, fileName):
    # Create qr code instance
    qr = qrcode.QRCode(version=None, box_size=10, border=4)
    
    # Add data
    qr.add_data(shortDomainName+url)
    qr.make(fit=True)
    
    # Create an SVG image factory
    factory = qrcode.image.svg.SvgPathImage
    
    # Generate the QR code as SVG
    img = qr.make_image(fill_color="white", back_color="transparent", image_factory=factory)
    
    # Save the SVG file
    img.save(fileName)
    #Change color
    with open(fileName, "r") as qr_img:
        content = qr_img.read()

    content = content.replace("#000000", "#777777") # a hex color string like "#FF0000"

    with open(fileName, "w+") as qr_img:
        qr_img.write(content)

    # Put image to S3
    PutObjectToS3(fileName, qrBucketName, qrBucketPrefix+'/'+fileName, 'image/svg+xml')
    os.remove(fileName)

# A function using Boto3 to scan DynamoDB Table returned as list of items
def scanDynamoDB(tableName):
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(tableName)
    response = table.scan()
    items = response['Items']
    return items
# Update st session all URL list.
def UpdateAllURL(tableName):
    st.session_state['allURL'] = scanDynamoDB(tableName);
    
# A function to PutItem into DynamoDB Table using boto3
def putItem(tableName, newShort, newOriginal):
    item =  {'url': newShort, 'redirect': newOriginal, 's3ImgPath': qrBucketPrefix+'/'+newShort+'.svg'} 
    url = item['url'];
    if url == '': return False;
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(tableName)
    table.put_item(
        Item=item
    )
    print(CreateQRSVG(url,url+'.svg'))

    UpdateAllURL(tableName)
    return True;

# A function to DeleteItem in DynamoDB Table matching key named url using boto3
def deleteItem(tableName, url):
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(tableName)
    table.delete_item(
        Key={
            'url': url
        }
    )
    return True;

# Get Item from DynamoDB from Key
def queryDynamoDB(tableName, urlPath, field):
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(tableName)
    print(tableName)
    print(urlPath)
    try:
        response = table.get_item(
            Key={
                'url': urlPath
            }
        )
        item = response.get('Item')
        
        print(item)
        if item is None:
            return "https://www.google.com/search?q="+urlPath
        return item[field]
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(error_code)
        print(error_message)
        
        return "https://www.google.com/search?q="+urlPath

# Main GUI
with open('./config/credential.yaml') as file:
    credential = yaml.load(file, Loader=SafeLoader)

# Pre-hashing all plain text passwords once
Hasher.hash_passwords(credential['credentials'])

authenticator = stauth.Authenticate(
    credential['credentials'],
    credential['cookie']['name'],
    credential['cookie']['key'],
    credential['cookie']['expiry_days'],
    credential['pre-authorized']
)


name, authentication_status, username = authenticator.login()

if st.session_state['authentication_status']:
    authenticator.logout('Logout', 'main')
    st.title('Create New URL')
    with st.form("new_url"):
        st.write("Input your new URL: ")
        #randURL = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(10))
        newShort = st.text_input('Short URL:', 'your-new-url')
        newOriginal = st.text_input('Origin URL:', 'https://example.com')
        submitButton = st.form_submit_button('   CREATE NEW SHORT   ')
        if submitButton:
            if putItem(tableName, newShort, newOriginal):
                st.toast('Successfully added URL: \n- URL: :green[' + newShort + "] created successfully.", icon='📄')
               
    st.header('Manage your URL List:',divider="green")
    UpdateAllURL(tableName)
    #print(st.session_state['allURL'] )
    items = st.session_state['allURL'];
    for item in items:
        container = st.container(border=True)
        with container:
            fullURL = shortDomainName+item['url']
            urlCol, deleteCol = st.columns([6, 1])
            urlCol.markdown("### URL: :green[**" + item['url']+ '**]')
            urlCol.code(fullURL)
            urlCol.write("Redirect: " + item['redirect'])
            #if deleteCol.button("Copy",key='copy'+item['url'], type="secondary"):
            #    pyperclip.copy(fullURL)
            #    st.toast('URL: ' + fullURL + " added to your clipboard.", icon='🎉')
            if deleteCol.button("Delete",key='delete'+item['url'], type="primary"):
                deleteItem(tableName, item['url'])
                UpdateAllURL(tableName)
                st.toast('URL: ' + fullURL + " deleted successfully.", icon='❌')
                sleep(0.5)
                #Refresh
                st.experimental_rerun()
            if 's3ImgPath' in item:
                imgName = item['url']+'.svg'
                imgSignedURL = GeneratePresignedURL(qrBucketName, qrBucketPrefix+'/'+imgName)
                if imgSignedURL is not None:
                    deleteCol.image(imgSignedURL)


elif st.session_state['authentication_status'] is False:
    st.error('Username/password is incorrect')
elif st.session_state['authentication_status'] is None:
    st.warning('Please enter your username and password')
