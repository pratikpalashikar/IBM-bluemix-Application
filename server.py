import os
import json
import keystoneclient.v3 as keystoneclient
import swiftclient.client as swiftclient
from flask import Flask, request, redirect,render_template,url_for,flash
from flask import send_from_directory
import pyDes
from flask.helpers import make_response

'''
Cloud Assignment 1 : IBM Bluemix datastore
Name: Pratik Palashikar
Student id : 1001227244
'''

'''
Refered materials:

[1]https://developer.ibm.com/recipes/tutorials/use-python-to-access-your-bluemix-object-storage/
[2]https://github.com/IBM-Bluemix/python-hello-world-flask
[3]https://www.ibm.com/blogs/cloud-computing/2014/08/getting-started-python-ibm-bluemix/
[4]https://developer.ibm.com/recipes/tutorials/using-ibm-object-storage-in-bluemix-with-python/
[5]http://twhiteman.netfirms.com/des.html
[6]http://www.laurentluce.com/posts/python-and-cryptography-with-pycrypto/
[7]http://blog.mattcrampton.com/post/31254835293/iterating-over-a-dict-in-a-jinja-template
[8]http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
'''



# Created a Python-Flask application to upload a file, retrieve and delete file from IBM bluemix cloud
app = Flask(__name__)

#Constants
authentication_url = ''
objectStorage_password=''
objectStorage_project_id=''
objectStorage_user_id=''
objectStorage_region_name=''
connection =''
container_name = 'bucket'


# default code when the app is generated using the ibm bluemix cloud
try:
  from SimpleHTTPServer import SimpleHTTPRequestHandler as Handler
  from SocketServer import TCPServer as Server
except ImportError:
  from http.server import SimpleHTTPRequestHandler as Handler
  from http.server import HTTPServer as Server


# Allowed extension for the files to be uploaded
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','docx'])

# Maximum size of the allowed file is 1MB
app.config['MAX_CONTENT_LENGTH']= 1*1024*1024

# Read port selected by the cloud for our application
PORT = int(os.getenv('VCAP_APP_PORT', 8080))

# Cloud credentials to connect ObjectStore
cloud_credential = json.loads(os.environ['VCAP_SERVICES'])['Object-Storage'][0]
objectstorage_credential = cloud_credential['credentials']
authentication_url = objectstorage_credential['auth_url'] + '/v3'  #authorization URL
objectStorage_password = objectstorage_credential['password']     #password
objectStorage_project_id = objectstorage_credential['projectId'] #project id
objectStorage_user_id = objectstorage_credential['userId']       #user id
objectStorage_region_name = objectstorage_credential['region']   #region name

# Establish the connection using the cloud credential
connection = swiftclient.Connection(key=objectStorage_password,
    authurl=authentication_url,
    auth_version='3',
    os_options={"project_id":objectStorage_project_id,
    "user_id": objectStorage_user_id,
    "region_name": objectStorage_region_name})

# if the container exits then return false else create the container and return
def createContainer():
    #Create a container to hold the objects as well create a container once
    print 'Inside create container'
    for container in connection.get_account()[1]:
        print container['name']
        return False
    # if container is not present then create the container
    connection.put_container(container_name)
    print('Container created successfully')
    return True

# Home page containing the UI to upload the file
@app.route('/')
def home():
    return render_template('home.html')

# [8] check for the allowed extension for the file name
def allowed_ext(filename):
    if '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
        return True
    else:
        return False

#[8] Upload file
@app.route('/uploadFile', methods=['GET', 'POST'])
def upload_file():
    #Create the container if the container does not exists
    print 'Inside upload file' #debug statement
    res = createContainer()
    print 'container created successfully' #debug statement
    totalFileSize = 0;
    #check before uploading the total files in the container
    for container in connection.get_account()[1]:
        for data in connection.get_container(container['name'])[1]:
            totalFileSize+=data['bytes']

    if totalFileSize < (10*1024*1024):
        if request.method == 'POST':
            # check if the post request has the file part
            if 'file' not in request.files:
                flash('No file part')
                return redirect(request.url)
            file = request.files['file']
            fileContent = file.read()
            fileLength = len(fileContent)
            print 'file Content'+fileContent
            #encrpyting the content
            # if user does not select file, browser also
            # submit a empty part without filename
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)

            if file and allowed_ext(file.filename):
                if fileLength < (1*1024*1024):
                    filename = file.filename
                    #encrpyt the file data before uploading
                    #[5] tried encrption using the GNUPG but didnt get the code working, tried other libraries as well but py DES is easy one
                    key = pyDes.des("DESCRYPT", pyDes.CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=pyDes.PAD_PKCS5)
                    data = key.encrypt(fileContent)
                    print 'Encrpyted data '+str(data)

                    #fileContent = file.read()
                    #print 'File content'+fileContent
                    '''with open(filename, 'r') as read_file:
                        fileContent=local_file.read().replace('\n', '')
                        print 'data'+fileContent'''
                    # Create a file for uploading
                    with open(filename, 'w') as local_file:
                        connection.put_object(container_name,
                        filename,
                        contents= data,
                        content_type='text/plain')
                    render_template('uploadSuccess.html')
                else:
                    return render_template('sizeexceed.html')
            else:
                return render_template('home.html')
        return render_template('uploadSuccess.html')
    else:
        return render_template('sizeexceed.html')


# get the list of all the files user has uploaded on the cloud
@app.route('/listFiles',methods=['GET','POST'])
def listFiles():
    #connection = establishConn()
    filesList = []
    hashMap = {}
    i=0
    for container in connection.get_account()[1]:
        for data in connection.get_container(container['name'])[1]:
            hashMap['fileName'+str(i)] = data['name']
            filesList.append(hashMap)
            i=i+1
    if not filesList:
        hashMap={}
        hashMap['Files'] = 'Empty'
        filesList.append(hashMap)
    return render_template('showList.html',resultset=filesList)

# delete a particular file from the list
@app.route('/deleteFile',methods=['GET','POST'])
def deleteFile():
    try:
        #connection = establishConn()
        file_name = request.args.get('filename')
        print 'Filename '+ file_name
        connection.delete_object(container_name,file_name)
    except:
       return render_template('correctName.html')
    return render_template('deleteSuccess.html')

#Doenload a file
@app.route('/downloadFile',methods=['GET','POST'])
def downloadFile():
    #connection = establishConn()
    try:
        file_name = request.args.get('filename')
        print 'Filename '+ file_name
        key = pyDes.des("DESCRYPT", pyDes.CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=pyDes.PAD_PKCS5)
        object = connection.get_object(container_name, file_name)
        with open(file_name, 'w') as local_file:
            local_file.write(key.decrypt(object[1]))
            print 'File temporarily written contains '+ str(key.decrypt(object[1]))
        get_response = make_response(str(object[1]))
        get_response.headers["Content-Disposition"] = "attachment; filename=" + file_name
        return  get_response
    except:
        return render_template('correctName.html')

    return render_template('downloadSuccess.html')
	
# main method
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)

