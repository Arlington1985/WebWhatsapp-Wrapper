import os, sys, time, json, filecmp, logging
from datetime import datetime, timedelta
from webwhatsapi import WhatsAPIDriver
from webwhatsapi.objects.message import Message, MediaMessage
from urllib.parse import urlparse
import psycopg2
from func_timeout import func_timeout, FunctionTimedOut



logging.basicConfig(level=logging.INFO)

logging.info ("Environment", os.environ)
try:
   os.environ["SELENIUM"]
except KeyError:
   logging.error("Please set the environment variable SELENIUM to Selenium URL")
   sys.exit(1)

try:
   mobile_number = os.environ["MOBILE_NUMBER"]
   iden_number = os.environ["IDEN_NUMBER"]
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
    driver.wait_for_login(timeout=99999999999)
    logging.info("Saving session")
    driver.save_firefox_profile(remove_old=True)
    logging.info("Bot started")
    database_url = urlparse(os.environ["DATABASE_URL"])
    username = database_url.username
    password = database_url.password
    database = database_url.path[1:]
    hostname = database_url.hostname
    port     = database_url.port
    
    db_conn = psycopg2.connect(
        database = database,
        user = username,
        password = password,
        host = hostname,
        port = port
    )
    logging.info('Connected to database')
    insert_to_downloads = """INSERT INTO whatsapp.downloads(filename, datetime, status, description, message_id, size, mime, caption, media_key)
             VALUES(%s, LOCALTIMESTAMP, %s, %s, %s, %s, %s, %s, %s ) RETURNING id;"""
    
    insert_to_chats = """INSERT INTO whatsapp.chats(datetime, message, message_id)
             VALUES(LOCALTIMESTAMP, %s, %s ) RETURNING id;"""

    insert_to_messages = """INSERT INTO whatsapp.messages(origin_id, message_type, message_timestamp, sender_msisdn, sender_name, datetime, receiver_msisdn)
             VALUES(%s, %s, %s, %s, %s, LOCALTIMESTAMP, %s ) RETURNING id;"""

    check_if_processed = """SELECT MAX(a.datetime) latest_process_time FROM (SELECT d.status, d.datetime FROM whatsapp.messages m, whatsapp.downloads d WHERE m.id=d.message_id AND m.origin_id=%s) a GROUP BY a.status HAVING status!='skipped' ORDER BY latest_process_time DESC LIMIT 1;"""

    loaded_contacts = """SELECT receiver_msisdn, sender_msisdn, earlier_messages FROM whatsapp.load_earlier_messages WHERE receiver_msisdn=%s AND sender_msisdn=%s AND earlier_messages=True;"""
    reloaded_contacts = """SELECT sender_msisdn FROM whatsapp.load_earlier_messages WHERE receiver_msisdn=%s AND earlier_messages=True;"""


    while True:
        time.sleep(3)
        logging.info('Checking for more messages, status, '+ driver.get_status())
        
        # Define reloaded contacts and process them
        logging.info("Getting reload contacts")
        with db_conn.cursor() as cur:
            cur.execute(reloaded_contacts, (str(mobile_number), ))
            reloaded_contacts_set=cur.fetchone()
        if reloaded_contacts_set is not None:
            logging.info("The contacts will be reloaded: "+reloaded_contacts_set)
            for chat in driver.get_all_chats():
                sender_msisdn=str(chat.id).split('@')[0]
                if sender_msisdn in reloaded_contacts_set:
                    create_directory(sender_msisdn)

                    # Load all earlier messages
                    logging.info("Loading earlier messages for: " +sender_msisdn+"...")
                    if chat.are_all_messages_loaded()==False:
                        chat.load_all_earlier_messages()
                        logging.info("Earlier messages loaded for: " +sender_msisdn)
                    else:
                        logging.info("All messages already loaded for: " +sender_msisdn)
                    
                    # Get loaded messages
                    messages=chat.get_messages()
                    process_messages(messages)
                    chat.send_seen()
                    logging.info("Sent seen request")
        else:
            logging.info("Nothing to reload, continue")


        # Read unread messages
        logging.info("Getting unread messages")
        for contact in driver.get_unread(use_unread_count=True, fetch_all_as_unread=True):
            logging.info(contact.chat)
            sender_msisdn=str(contact.chat.id).split('@')[0]
            create_directory(sender_msisdn)
            logging.info("Messages will be processed for "+sender_msisdn)
            process_messages(contact.messages)
            contact.chat.send_seen()
            logging.info("Sent seen request")


            
except Exception as e:
    logging.exception(e)
    if 'driver' in locals() and driver is not None:
        driver.close()
        logging.info('Selenium driver connection closed')        
    if 'db_conn' in locals() and db_conn is not None:
        db_conn.close()
        logging.info('Database connection closed')
    raise
finally:
    if 'driver' in locals() and driver is not None:
        driver.close()
        logging.info('Selenium driver connection closed')        
    if 'db_conn' in locals() and db_conn is not None:
        db_conn.close()
        logging.info('Database connection closed')



def process_messages(messages):
    logging.info("Loaded message count: " +str(len(messages)))
    for message in messages:
        logging.info ('class: '+ str(message.__class__.__name__))
        logging.info ('message: '+ str(message))
        logging.info ('id: '+ str(message.id))
        logging.info ('type: '+ str(message.type))
        logging.info ('timestamp: '+ str(message.timestamp))
        logging.info ('chat_id: '+ str(message.chat_id))
        logging.info ('sender: '+ str(message.sender))
        logging.info ('sender.id: '+ str(message.sender.id))
        logging.info ('sender.safe_name: '+ str(message.sender.get_safe_name()))
        
        with db_conn.cursor() as cur:
            cur.execute(check_if_processed, (str(message.id), ))
            result_set=cur.fetchone()

        if result_set is None: 
            if message.type == 'chat':
                logging.info ('-- Chat')
                logging.info ('safe_content: '+ str(message.safe_content))
                logging.info ('content: '+ str(message.content))
                with db_conn.cursor() as cur:
                    cur.execute(insert_to_messages, (str(message.id), str(message.type), str(message.timestamp), str(message.chat_id['user'][:12]), str(message.sender.get_safe_name()), str(mobile_number)))
                    message_id = cur.fetchone()[0]
                    cur.execute(insert_to_chats, (str(message.content), int(message_id)))
                    chat_id = cur.fetchone()[0]
                    db_conn.commit()

            elif message.type == 'image' or message.type == 'video' :
                logging.info ('-- Image or Video')
                logging.info ('filename: '+ str(message.filename))
                logging.info ('size: '+ str(message.size))
                logging.info ('mime: '+ str(message.mime))
                logging.info ('caption: '+ str(message.caption))
                logging.info ('media_key: '+ str(message.media_key))
                logging.info ('client_url: '+ str(message.client_url))

                file_split=os.path.splitext(str(message.filename))
                new_file_name=file_split[0]+f"_{iden_number}"+file_split[1]
                try:
                    downloaded_file=func_timeout(5, message.save_media, args=(dirName, True))
                    os.rename(downloaded_file, os.path.join(dirName, new_file_name))
                    logging.info(f"Photo downloaded to {dirName} folder")
                    status='downloaded'
                except (Exception, FunctionTimedOut) as ex:
                    logging.exception("Cannot download photo, skipping")
                    status='skipped'
                    
                with db_conn.cursor() as cur:
                    cur.execute(insert_to_messages, (str(message.id), str(message.type), str(message.timestamp), str(message.chat_id['user'][:12]), str(message.sender.get_safe_name()), str(mobile_number)))
                    message_id = cur.fetchone()[0]
                    cur.execute(insert_to_downloads, (new_file_name, status, None, int(message_id), int(message.size), str(message.mime), str(message.caption), str(message.media_key)))
                    download_id = cur.fetchone()[0]
                    db_conn.commit()
            else:
                logging.info ('-- Other')
        else:
            process_time = result_set[0]
            logging.info("Already processed on "+str(process_time))
    return True


def create_directory(sender_msisdn):
    # Creating directory tree
    dirName=os.path.join("/wphotos", sender_msisdn)
    if not os.path.exists(dirName):
        # exist_ok=True, because of paralel execution in another container, to avoid race condition 
        os.makedirs(dirName, exist_ok=True)
        logging.info("Directory set " + dirName +  " was created ")
    else:
        logging.info("Directory set " + dirName + " already exists")
    return True