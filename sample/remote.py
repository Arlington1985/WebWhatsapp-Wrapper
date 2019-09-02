import os, sys, time, json
from webwhatsapi import WhatsAPIDriver
from webwhatsapi.objects.message import Message, MediaMessage

print ("Environment", os.environ)
try:
   os.environ["SELENIUM"]
except KeyError:
   print("Please set the environment variable SELENIUM to Selenium URL")
   sys.exit(1)

try:
   os.environ["MOBILE_NUMBER"]
except KeyError:
   print("Please set the mobile number variable")
   sys.exit(1)

##Save session on "/firefox_cache/localStorage.json".
##Create the directory "/firefox_cache", it's on .gitignore
##The "app" directory is internal to docker, it corresponds to the root of the project.
##The profile parameter requires a directory not a file.
profiledir=os.path.join(".","firefox_cache",os.environ["MOBILE_NUMBER"])
if not os.path.exists(profiledir): 
    os.makedirs(profiledir)

driver = WhatsAPIDriver(profile=profiledir, client='remote', command_executor=os.environ["SELENIUM"])
print("Waiting for QR")
driver.wait_for_login(timeout=9999999999)
print("Saving session")
driver.save_firefox_profile(remove_old=False)
print("Bot started")

while True:
    time.sleep(3)
    print('Checking for more messages, status, '+ driver.get_status())
    for contact in driver.get_unread(use_unread_count=True):
        for message in contact.messages:
            print(json.dumps(message.get_js_obj(), indent = 4))
            print ('class', message.__class__.__name__)
            print ('message', message)
            print ('id', message.id)
            print ('type', message.type)
            print ('timestamp', message.timestamp)
            print ('chat_id', message.chat_id)
            print ('sender', message.sender)
            print ('sender.id', message.sender.id)
            print ('sender.safe_name', message.sender.get_safe_name())
            if message.type == 'chat':
                print ('-- Chat')
                print ('safe_content', message.safe_content)
                print ('content', message.content)
                # contact.chat.send_message(message.safe_content)
            elif message.type == 'image' or message.type == 'video' :
                print ('-- Image or Video')
                print ('filename', message.filename)
                print ('size', message.size)
                print ('mime', message.mime)
                print ('caption', message.caption)
                print ('client_url', message.client_url)
                dirName=os.path.join("/wphotos", message.chat_id['user'])
                if not os.path.exists(dirName):
                    os.mkdir(dirName)
                    print("Directory " , dirName ,  " created ")
                else:
                    print("Directory " , dirName , " already exists")
                message.save_media('./'+dirName+'/', force_download = True)
                contact.chat.send_seen()
                #contact.chat.send_message("Photo received")
            else:
                print ('-- Other')
