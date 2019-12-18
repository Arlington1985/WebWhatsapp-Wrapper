import os, sys, time, json, filecmp, logging
from webwhatsapi import WhatsAPIDriver
from webwhatsapi.objects.message import Message, MediaMessage

logging.basicConfig(level=logging.INFO)

logging.info ("Environment", os.environ)
try:
   os.environ["SELENIUM"]
except KeyError:
   logging.error("Please set the environment variable SELENIUM to Selenium URL")
   sys.exit(1)

try:
   mobile_number = os.environ["MOBILE_NUMBER"]
   last_mnumber = mobile_number[-1:]
except KeyError:
   logging.error("Please set the mobile number variable")
   sys.exit(1)

##Save session on "/firefox_cache/localStorage.json".
##Create the directory "/firefox_cache", it's on .gitignore
##The "app" directory is internal to docker, it corresponds to the root of the project.
##The profile parameter requires a directory not a file.
profiledir=os.path.join(".","firefox_cache", mobile_number)
if not os.path.exists(profiledir): 
    os.makedirs(profiledir)

driver = WhatsAPIDriver(profile=profiledir, client='remote', command_executor=os.environ["SELENIUM"])
try:
    logging.info("Waiting for QR")
    driver.wait_for_login(timeout=9999999999)
    logging.info("Saving session")
    driver.save_firefox_profile(remove_old=True)
    logging.info("Bot started")


    while True:
        time.sleep(3)
        logging.info('Checking for more messages, status, '+ driver.get_status())
        for contact in driver.get_unread(use_unread_count=True, fetch_all_as_unread=True):
            logging.info(contact)
            for message in contact.messages:
                logging.info ('class: '+ str(message.__class__.__name__))
                logging.info ('message: '+ str(message))
                logging.info ('id: '+ str(message.id))
                logging.info ('type: '+ str(message.type))
                logging.info ('timestamp: '+ str(message.timestamp))
                logging.info ('chat_id: '+ str(message.chat_id))
                logging.info ('sender: '+ str(message.sender))
                logging.info ('sender.id: '+ str(message.sender.id))
                logging.info ('sender.safe_name: '+ str(message.sender.get_safe_name()))
                if message.type == 'chat':
                    logging.info ('-- Chat')
                    logging.info ('safe_content: '+ str(message.safe_content))
                    logging.info ('content: '+ str(message.content))
                    # contact.chat.send_message(message.safe_content)
                elif message.type == 'image' or message.type == 'video' :
                    logging.info ('-- Image or Video')
                    logging.info ('filename: '+ str(message.filename))
                    logging.info ('size: '+ str(message.size))
                    logging.info ('mime: '+ str(message.mime))
                    logging.info ('caption: '+ str(message.caption))
                    logging.info ('client_url: '+ str(message.client_url))

                    # Creating directory tree
                    dirName=os.path.join("/wphotos", message.chat_id['user'][:12])
                    tmp_dir=os.path.join(dirName,"tmp")

                    if not os.path.exists(tmp_dir):
                        # Will create dirName and tmp_dir in one shoot
                        # exist_ok=True, because of paralel execution in another container, to avoid race condition 
                        os.makedirs(tmp_dir, exist_ok=True)
                        logging.info("Directory set " + tmp_dir +  " was created ")
                    else:
                        logging.info("Directory set " + tmp_dir + " already exists")

                    # Downloading file
                    try:
                        tmp_file=message.save_media(tmp_dir, force_download = True)
                        file_split=os.path.splitext(os.path.basename(tmp_file))
                    except Exception as ex:
                        logging.error("Cannot download photo, skipping")
                        continue

                    #driver.delete_message(contact.chat.id,message)
                    logging.info("Photo downloaded to "+tmp_file)
                    logging.info("Comparing with old photos")
                    old_files=[f for f in os.listdir(dirName) if os.path.isfile(os.path.join(dirName, f))]
                    if old_files:
                        logging.info(old_files)
                        dublicated=False
                        dublicated_with=[]
                        for old_file in old_files:
                            if filecmp.cmp(os.path.abspath(os.path.join(dirName, old_file)), tmp_file):
                                dublicated=True
                                dublicated_with.append(old_file)

                                
                        if dublicated:
                            os.remove(tmp_file)
                            logging.info("Photo duplicated with "+','.join(dublicated_with)+", removed")
                        else:
                            os.rename(tmp_file, os.path.join(dirName, file_split[0], f"_{last_mnumber}", file_split[1]))
                            logging.info("Photo moved to permanent location")
                    else:
                        os.rename(tmp_file, os.path.join(dirName, file_split[0], f"_{last_mnumber}", file_split[1]))
                        logging.info("First download, photo moved to permanent location")
                    #contact.chat.send_message("Photo received")
                else:
                    logging.info ('-- Other')
            contact.chat.send_seen()
            logging.info("Sent seen request")
except Exception as e:
	logging.exception(e)
	driver.close()
	raise
