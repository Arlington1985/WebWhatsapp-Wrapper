import os, sys, time, json, filecmp
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
driver.save_firefox_profile(remove_old=True)
print("Bot started")

try:
    while True:
        time.sleep(3)
        print('Checking for more messages, status, '+ driver.get_status())
        for contact in driver.get_unread(use_unread_count=True):
            for message in contact.messages:
                #print(json.dumps(message.get_js_obj(), indent = 4))
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

                    # Creating directory tree
                    dirName=os.path.join("/wphotos", message.chat_id['user'])
                    tmp_dir=os.path.join(dirName,"tmp")
                    if not os.path.exists(dirName):
                        os.mkdir(dirName)
                        print("Directory " , dirName ,  " created ")
                        os.mkdir(tmp_dir)
                        print("Directory " , tmp_dir ,  " created ")
                    else:
                        print("Directory " , dirName , " already exists")
                        if not os.path.exists(tmp_dir):
                            os.mkdir(tmp_dir)
                            print("Directory " , tmp_dir ,  " created ")

                    # Downloading file
                    tmp_file=message.save_media(tmp_dir, force_download = True)
                    print("Photo downloaded to ",tmp_file)
                    print("Comparing with old photos")
                    old_files=[f for f in os.listdir(dirName) if os.path.isfile(os.path.join(dirName, f))]
                    if old_files:
                        print(old_files)
                        dublicated=False
                        for old_file in old_files:
                            if filecmp.cmp(os.path.abspath(os.path.join(dirName, old_file)), tmp_file):
                                dublicated=True
                                
                        if dublicated:
                            os.remove(tmp_file)
                            print("Photo duplicated, removed")
                        else:
                            os.rename(tmp_file, os.path.join(dirName, os.path.basename(tmp_file)))
                            print("Photo moved to permanent location")
                    else:
                        os.rename(tmp_file, os.path.join(dirName, os.path.basename(tmp_file)))
                        print("First download, photo moved to permanent location")
                    contact.chat.send_seen()
                    print("Sent seen request")
                    #contact.chat.send_message("Photo received")
                else:
                    print ('-- Other')
except Exception as e:
	print('EXCEPTION:',e)
	driver.close()
	raise