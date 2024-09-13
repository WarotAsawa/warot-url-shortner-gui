import streamlit as st 
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.hasher import Hasher
import boto3
from botocore.exceptions import ClientError
import yaml
from yaml.loader import SafeLoader
import qrcode
import qrcode.image.svg

#import pyperclip
from time import sleep
st.session_state['allURL'] = []
st.session_state['newURL'] = ''
st.session_state['newRedirect'] = ''
st.set_page_config(page_title="WAROT SHORTENNER")
bucketName = 'warot-shorten-qr-collection'
tableName = 'warot-short-url-table'

# Gen SVG QR Code
def CreateQRSVG(url):
    factory = qrcode.image.svg.SvgImage
    img = qrcode.make(str(url), image_factory=factory)
    print(img)
    return img;
# A function using Boto3 to scan DynamoDB Table returned as list of items
def scanDynamoDB(tableName):
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
    table = dynamodb.Table(tableName)
    response = table.scan()
    items = response['Items']
    return items
# Update st session all URL list.
def UpdateAllURL(tableName):
    st.session_state['allURL'] = scanDynamoDB(tableName);
    
# A function to PutItem into DynamoDB Table using boto3
def putItem(tableName, item):
    if item['url'] == '': return False;
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
    table = dynamodb.Table(tableName)
    table.put_item(
        Item=item
    )
    print(CreateQRSVG(item['url']))

    UpdateAllURL(tableName)
    return True;

# A function to DeleteItem in DynamoDB Table matching key named url using boto3
def deleteItem(tableName, url):
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
    table = dynamodb.Table(tableName)
    table.delete_item(
        Key={
            'url': url
        }
    )
    return True;

# Main GUI
with open('./config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Pre-hashing all plain text passwords once
Hasher.hash_passwords(config['credentials'])

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['pre-authorized']
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
            if putItem(tableName, {'url': newShort, 'redirect': newOriginal}):
                st.toast('Successfully added URL: \n- URL: :green[' + newShort + "] created successfully.", icon='📄')
               
    st.header('Manage your URL List:',divider="green")
    UpdateAllURL(tableName)
    #print(st.session_state['allURL'] )
    items = st.session_state['allURL'];
    for item in items:
        container = st.container(border=True)
        with container:
            fullURL = "http://short.warot.dev/"+item['url']
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

elif st.session_state['authentication_status'] is False:
    st.error('Username/password is incorrect')
elif st.session_state['authentication_status'] is None:
    st.warning('Please enter your username and password')


def queryDynamoDB(tableName, urlPath, field):
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
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
