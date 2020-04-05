#!/usr/bin/env python
import youtube_dl
import requests
import sys
import sqlite3
import os
import http.cookiejar
import urllib.parse as urlparse
from prettytable import PrettyTable
from sqlite3 import Error
from bs4 import BeautifulSoup
import subprocess
import time
import sql

###### Config
database = "./database.db"
AutoUp = True #自動上傳
Remote = "PH:"
upload_command = "rclone move -v \"{}\" \"{}\" --log-file=upload.log" #Rename Command

##### Pre Process
Premium = True if os.path.exists('cookies.txt') else False
headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36'}
cj = http.cookiejar.MozillaCookieJar('cookies.txt')
cj.load()

##### Add Videos
def add_all_items(conn,only_new=True):
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM ph_items WHERE new='1'") if only_new else c.execute("SELECT * FROM ph_items")
    except Error as e:
        print(e)
        sys.exit()

    rows = c.fetchall()
    for row in rows:
        if str(row[1]) == "model":
            url_after = "/videos/upload"
        elif str(row[1]) == "pornstar":
            url_after = "/videos"
        elif str(row[1]) == "users":
            url_after = "/videos/public"
        elif str(row[1]) == "channels":
            url_after = "/videos"
        else:
            url_after = ""

        subpath = '/' + str(row[1]) + '/' + str(row[3])
        url = ("https://www.pornhub.com/" if not Premium else "https://www.pornhubpremium.com/" ) + str(row[1]) + "/" + str(row[2]) + url_after + '?o=da'
        Data = get_channel(url, go_next_page=not only_new) #非新的只爬一頁
        #print("Start  : Input %d videos from %s" % (len(Data.keys()), subpath))
        for key in Data.keys():
            line = [key,subpath,Data[key],0,time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) ,'']
            sql.input(database,'ph_videos',line)
        print("Finish : Input %d videos from %s" % (len(Data.keys()), subpath))

        try:
            c.execute("UPDATE ph_items SET new='0', lastchecked=? WHERE url_name=?", (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), row[2],) )
            conn.commit()
        except Error as e:
            print(e)
            sys.exit()


def get_channel(url,go_next_page=True):
    print("Search :",url)
    response=requests.get(url,headers=headers,cookies=cj)
    response.encoding = 'UTF-8'
    soup = BeautifulSoup(response.text, 'lxml')
    videos = soup.find("div",{"class":"rightSide floatRight"}).find("div",{"class":"widgetContainer"}).find_all("li",{"class":"pcVideoListItem"})
    Data = {video.get("_vkey"):video.find("span",{"class":"title"}).getText().strip() for video in videos}

    next_page = soup.find("li",{"class":"page_next"}) #Next
    if next_page != None and go_next_page:
        url = "https://www.pornhubpremium.com" + next_page.find("a").get("href")
        Data.update(get_channel(url))
    return Data

##################################### CHECKINGS 

def type_check(item):
    if item == "model":
        print ("Valid type (model) selected.")
    elif item == "pornstar":
        print ("Valid type (pornstar) selected.")
    elif item == "channels":
        print ("Valid type (channel) selected.")
    elif item == "users":
        print ("Valid type (user) selected.")
    elif item == "playlist":
        print ("Valid type (playlist) selected.")
    elif item == "all":
        print ("Valid type (all) selected.")
    else:
        how_to_use("Not a valid type.")
        sys.exit()

def ph_url_check(url):
    parsed = urlparse.urlparse(url)
    if Premium and (parsed.netloc == "www.pornhub.com" or parsed.netloc == "www.pornhubpremium.com"):
        print ("PornHub url validated.")
    elif not Premium and parsed.netloc == "www.pornhub.com":
        print ("PornHub url validated.")
    else:
        print ("This is not a PornHub url.")
        sys.exit()

def ph_type_check(url):
    parsed = urlparse.urlparse(url)
    if parsed.path.split('/')[1] == "model":
        print ("This is a MODEL url,")
    elif parsed.path.split('/')[1] == "pornstar":
        print ("This is a PORNSTAR url,")
    elif parsed.path.split('/')[1] == "channels":
        print ("This is a CHANNEL url,")
    elif parsed.path.split('/')[1] == "users":
        print ("This is a USER url,")
    elif parsed.path.split('/')[1] == "playlist":
        print ("This is a PLAYLIST url,")
    elif parsed.path.split('/')[1] == "view_video.php":
        print ("This is a VIDEO url. Please paste a model/pornstar/user/channel/playlist url.")
        sys.exit()
    else:
        print ("Somethings wrong with the url. Please check it out.")
        sys.exit()

def ph_alive_check(url):
    request = requests.get(url,headers=headers,cookies=cj)
    if request.status_code == 200:
        print ("and the URL is existing.")
    else:
        print ("but the URL does not exist.")
        sys.exit()

def add_check(name_check):
    if name_check == "batch":
        u_input = input("Please enter full path to the batch-file.txt (or c to cancel): ")
        if u_input == "c":
            print("Operation canceled.")
        else:
            with open(u_input, 'r') as input_file:
                for line in input_file:
                    line = line.strip()
                    add_item(line)

    else:
        add_item(name_check)


def get_item_name(item_type, url_item):
    url = url_item
    '''html = request.urlopen(url).read().decode('utf8')
    html[:60]'''
    html=requests.get(url,headers=headers,cookies=cj)
    html.encoding = 'UTF-8'
    #soup = BeautifulSoup(html, 'html.parser')
    soup = BeautifulSoup(html.text, 'lxml')
    if item_type == "model":
        finder = soup.find(class_='nameSubscribe')
        title = finder.find(itemprop='name').text.replace('\n','').strip()
    elif item_type == "pornstar":
        finder = soup.find(class_='nameSubscribe')
        title = finder.find(class_='name').text.replace('\n','').strip()
    elif item_type == "channels":
        finder = soup.find(class_='bottomExtendedWrapper')
        title = finder.find(class_='title').text.replace('\n','').strip()
    elif item_type == "users":
        finder = soup.find(class_='bottomInfoContainer')
        title = finder.find('a', class_='float-left').text.replace('\n','').strip()
    elif item_type == "playlist":
        finder = soup.find(id='playlistTopHeader')
        title = finder.find(id='watchPlaylist').text.replace('\n','').strip()
    else:
        print("No valid item type.")

    return title

##################################### DOWNLOADIN
def dl_all_videos(conn):
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM ph_videos WHERE finished='0'")
    except Error as e:
        print(e)
        sys.exit()
    rows = c.fetchall()
    for row in rows:
        name = row[2].replace("\"","\'")
        file_path = get_dl_location('DownloadLocation') + row[1] + '/'+ name +'.mp4'
        if os.path.exists(file_path):
            pass
        else:
            if os.path.exists(file_path+'.part'): #移除未完成的檔案
                print('Exist unfinished files.')
                os.remove(file_path+'.part')
            url = 'https://www.pornhub%s.com/view_video.php?viewkey=%s' % ('premium' if Premium else '', row[0])
            file_path = custom_dl_download(url,row[1])
            if not os.path.exists(file_path) : #如果下載失敗(不存在預計檔名的檔案)
                print("FailDL :",row[0])
                continue

        if AutoUp: #自動上傳，採用併發
            destination = Remote + row[1]
            print("Upload :",row[2])
            subprocess.Popen(upload_command.format(file_path,destination),shell=True)

        try:
            c.execute("UPDATE ph_videos SET finished='1', finish_time=? WHERE viewkey=?", (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), row[0],))
            conn.commit()
        except Error as e:
            print(e)
            sys.exit()

def dl_start():
    conn = create_connection(database)
    with conn:
        print("add new items")
        add_all_items(conn)
        dl_all_videos(conn)

        print("add all items")
        add_all_items(conn,only_new=False)
        dl_all_videos(conn)




def custom_dl(name_check):
    if name_check == "batch":
        u_input = input("Please enter full path to the batch-file.txt (or c to cancel): ")
        if u_input == "c":
            print("Operation canceled.")
        else:
            with open(u_input, 'r') as input_file:
                for line in input_file:
                    line = line.strip()
                    custom_dl_download(line)

    else:
        custom_dl_download(name_check)


def custom_dl_download(url,subpath='/handpicked'):
    ph_url_check(url)
    ph_alive_check(url)

    outtmpl = get_dl_location('DownloadLocation') + subpath + '/%(title)s.%(ext)s'
    ydl_opts = {
        'format': 'best',
        'outtmpl': outtmpl,
        'nooverwrites': True,
        'no_warnings': False,   
        'ignoreerrors': True,
        'cookiefile':'cookies.txt',
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url,download=True)
        file_path = ydl.prepare_filename(info)
        #x = ydl.download([url])
        return file_path


def add_item(name_check):
    parsed = urlparse.urlparse(name_check)
    ph_url_check(name_check)
    ph_type_check(name_check)
    ph_alive_check(name_check)
    item_type = parsed.path.split('/')[1]
    item_url_name = parsed.path.split('/')[2]
    item_name = get_item_name(item_type, name_check)
    
    conn = create_connection(database)
    c = conn.cursor()
    try:
        c.execute("SELECT count(*) FROM ph_items WHERE url_name = ?", (item_name,))
    except Error as e:
        print(e)
        sys.exit()

    data=c.fetchone()[0]
    if data==0:
        with conn:
            item = (item_type, item_url_name, item_name, '1');
            item_id = create_item(conn, item)

        print(item_name + " added to database.")
    else:
        print("Item already exists in database")


##################################### DATABASE ORIENTED

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)
    return conn


def create_item(conn, item):
    sql = ''' INSERT INTO ph_items(type,url_name,name,new)
              VALUES(?,?,?,?) '''
    c = conn.cursor()
    c.execute(sql, item)
    return c.lastrowid


def select_all_items(conn, item):
    c = conn.cursor()
    if item == "all":
        c.execute("SELECT * FROM ph_items")
    else:
        c.execute("SELECT * FROM ph_items WHERE type='" + item + "'")
 
    rows = c.fetchall()
 
    t = PrettyTable(['Id.', 'Name', 'Type', 'Date created', 'Last checked', 'Url'])
    t.align['Id.'] = "l"
    t.align['Name'] = "l"
    t.align['Type'] = "l"
    t.align['Date created'] = "l"
    t.align['Last checked'] = "l"
    t.align['Url'] = "l"
    for row in rows:
        url = ("https://www.pornhub.com/" if not Premium else "https://www.pornhubpremium.com/" ) + str(row[1]) + "/" + str(row[2])
        t.add_row([row[0], row[3], row[1], row[5], row[6], url])
    print(t)


def list_items(item):
    conn = create_connection(database)
    with conn:
        print("Listing items from database:")
        select_all_items(conn, item)


def delete_single_item(conn, id):
    sql = 'DELETE FROM ph_items WHERE id=?'
    c = conn.cursor()
    c.execute(sql, (id,))
    conn.commit()


def delete_item(item_id):
    conn = create_connection(database)
    with conn:
        delete_single_item(conn, item_id);


def create_config(conn, item):
    sql = ''' INSERT INTO ph_settings(option, setting)
              VALUES(?,?) '''
    c = conn.cursor()
    c.execute(sql, item)
    return c.lastrowid


def prepare_config():
    conn = create_connection(database)
    u_input = input("Please enter the FULL PATH to your download location: ")
    with conn:
        item = ('DownloadLocation', u_input)
        item_id = create_config(conn, item)


def get_dl_location(option):
    conn = create_connection(database)
    if conn is not None:
        c = conn.cursor()
        c.execute("SELECT * FROM ph_settings WHERE option='" + option + "'")
     
        rows = c.fetchall()
     
        for row in rows:
            dllocation = row[2]
        return dllocation

    else:
        print("Error! somethings wrong with the query.")


def check_for_database():
    print("Running startup checks...")
    if os.path.exists(database) == True:
        print("Database exists.")
    else:
        print("Database does not exist.")
        print("Looks like this is your first time run...")
        first_run()

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
        print("Tables created.")
    except Error as e:
        print(e)

def create_tables(): 
    sql_create_items_table = """ CREATE TABLE IF NOT EXISTS ph_items (
                                        id integer PRIMARY KEY,
                                        type text,
                                        url_name text,
                                        name text,
                                        new integer DEFAULT 1,
                                        datecreated DATETIME DEFAULT CURRENT_TIMESTAMP,
                                        lastchecked DATETIME DEFAULT CURRENT_TIMESTAMP
                                    ); """

    sql_create_vidoes_table = """ CREATE TABLE IF NOT EXISTS ph_videos (
                                        viewkey text PRIMARY KEY,
                                        subpath text,
                                        name text,
                                        finished integer DEFAULT 0,
                                        add_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                                        finish_time DATETIME DEFAULT CURRENT_TIMESTAMP
                                    ); """

    sql_create_settings_table = """ CREATE TABLE IF NOT EXISTS ph_settings (
                                        id integer PRIMARY KEY,
                                        option text,
                                        setting text,
                                        datecreated DATETIME DEFAULT CURRENT_TIMESTAMP
                                    ); """
 
    # create a database connection
    conn = create_connection(database)
 
    # create tables
    if conn is not None:
        # create items table
        create_table(conn, sql_create_items_table)
        create_table(conn, sql_create_vidoes_table)
        create_table(conn, sql_create_settings_table)
        prepare_config()
    else:
        print("Error! cannot create the database connection.")


##################################### Lets do it baby

def first_run():
    create_tables()

##################################### MESSAGING

def how_to_use(error):
    print("Error: " + error)
    print("Please use the tool like this:")
    t = PrettyTable(['Tool', 'command', 'item'])
    t.align['Tool'] = "l"
    t.align['command'] = "l"
    t.align['item'] = "l"
    t.add_row(['phdler', 'start', ''])
    t.add_row(['phdler', 'custom', 'url (full PornHub url) | batch (for .txt file)'])
    t.add_row(['phdler', 'add', 'model | pornstar | channel | user | playlist | batch (for .txt file)'])
    t.add_row(['phdler', 'list', 'model | pornstar | channel | user | playlist | all'])
    t.add_row(['phdler', 'delete', 'model | pornstar | channel | user | playlist'])
    print(t)

def help_command():
    print("------------------------------------------------------------------")
    print("You asked for help, here it comes! Run phdler with these commands:")
    t = PrettyTable(['Command', 'argument', 'description'])
    t.align['Command'] = "l"
    t.align['argument'] = "l"
    t.align['description'] = "l"
    t.add_row(['start', '', 'start the script'])
    t.add_row(['custom', 'url | batch', 'download a single video from PornHub'])
    t.add_row(['add', 'model | pornstar | channel | user | playlist | batch (for .txt file)', 'adding item to database'])
    t.add_row(['list', 'model | pornstar | channel | user | playlist', 'list selected items from database'])
    t.add_row(['delete', 'model | pornstar | channel | user | playlist', 'delete selected items from database'])
    print(t)
    print("Example: phdler add pornhub-url")
    print("------------------------------------------------------------------")