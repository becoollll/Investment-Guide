from FinMind.data import DataLoader
import pymysql
import mysql.connector
import datetime
import time
import logging

now_time = datetime.datetime.now()
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M',
                    handlers=[logging.FileHandler(f'./maintain/log/{now_time}.log', 'w', 'utf-8'), ])

################# 取得各家公司代號 #################
db=pymysql.connect(host='localhost', port=3306, user='username', password = 'password', db = 'database', charset ='utf8')
cursor = db.cursor()
sql = "SELECT `cid` FROM `company`;"
#sql = "SELECT DISTINCT id FROM `closingprice` WHERE id not in (SELECT id FROM closingprice WHERE `date` = '2023-01-03');"
cursor.execute(sql)
rows = cursor.fetchall()
code = [row[0] for row in rows]
print(code)


################# 各家公司2023的收盤價 #################
yesterday = now_time + datetime.timedelta(days = -1)
end_date = yesterday.strftime('%Y-%m-%d')

fivedays = now_time + datetime.timedelta(days = -5)
start_date = fivedays.strftime('%Y-%m-%d')


###### for分批(~1006) ######
start = 600+334
end = len(code)
#code[88](4144),4414,3018,3536
for i in range(start,end):
    stock_no = code[i]
    print("now doing: ", code[i], ", ", i)

    try:
        df = DataLoader()
        df.login_by_token(api_token='api_token_here')
        df.login(user_id='userid',password='password')
        temp = df.taiwan_stock_daily(stock_id = stock_no, start_date=start_date, end_date=end_date)
        temp.drop(columns=["Trading_money", "open", "max", "min", "spread", "Trading_turnover"], inplace=True)
        #print(temp)
        for j in range(len(temp)):
            #print(temp.loc[i][0], temp.loc[i],[1], type(float(temp.loc[i][2])))
            #print(temp.loc[j][1],",", temp.loc[j][0],",", temp.loc[j][2])
            
            db=pymysql.connect(host='localhost', port=3306, user='username', password = 'password', db = 'database', charset ='utf8')
            cursor = db.cursor()
            #sql_id = "INSERT INTO ClosingPrice VALUES('" + temp.loc[i][0] + "', '" + temp.loc[i][1] + "', '" + float(temp.loc[i][2]) + "')"
            check_id = f"SELECT * FROM `ClosingPrice` WHERE `id` = '{temp.loc[j][1]}' AND `date`='{temp.loc[j][0]}';"
            cursor.execute(check_id)
            rows = cursor.fetchone()
            if (rows):
            	continue
            print(temp.loc[j][1],",", temp.loc[j][0],",", temp.loc[j][3],",", temp.loc[j][2])	
            sql_id = "INSERT INTO ClosingPrice (`id`, `date`, `price`, `volumn`) VALUES('" + temp.loc[j][1] + "', '" + temp.loc[j][0] + "', {},{})".format(float(temp.loc[j][3]),temp.loc[j][2])
            
            try:
                cursor.execute(sql_id)
                db.commit()
                logging.info(f"{temp.loc[j][1]} update")
            except mysql.connector.Error as error:
                db.rollback()
                print("Failed to add id into table {}".format(error), temp[i])

            db.close()
    except:
        print("wrong:", code[i], ",", i)

db=pymysql.connect(host='localhost', port=3306, user='username', password = 'password', db = 'database', charset ='utf8')

cursor = db.cursor()
sql_date = f"SELECT DISTINCT date FROM `ClosingPrice` WHERE `date` BETWEEN '{start_date}' AND '{end_date}';"
cursor.execute(sql_date)
rows = cursor.fetchall()
d = [row[0] for row in rows]
print(d)

seconds = time.time()
year = time.localtime(seconds).tm_year-1

for i in range(len(d)):
    date = d[i]
    print(date,year)
    try:
        sql_delete_pbr = f"DELETE FROM `pbr` WHERE date = '{date}';"
        cursor.execute(sql_delete_pbr)
        db.commit()
        print("delete per ok")
    except:
        db.rollback()
        print("error  DELETE pbr ----  ",date)
    try:
        sql_delete_per = f"DELETE FROM `per` WHERE date = '{date}';"
        cursor.execute(sql_delete_per)
        db.commit()
        print("delete pbr ok")
    except:
        db.rollback()
        print("error  DELETE per ----  ",date)

    sql_per = f"INSERT INTO per (id,date,val) SELECT p.id,p.date,round((p.price/e.val),2) FROM ClosingPrice p,eps e where e.year = '{year}' and p.date = '{date}' and  p.id = e.id and e.val != 0;"
    sql_pbr = f"INSERT INTO pbr (id,date,val) SELECT p.id,p.date,round((p.price/b.val),2) FROM ClosingPrice p,bps b where b.year = '{year}' and p.date = '{date}' and  p.id = b.id and b.val != 0;"
    sql_per_z = f"INSERT INTO per (id,date,val) SELECT p.id,p.date,e.val FROM ClosingPrice p,eps e where e.year = '{year}' and p.date = '{date}' and  p.id = e.id and e.val = 0;"
    sql_pbr_z = f"INSERT INTO pbr (id,date,val) SELECT p.id,p.date,b.val FROM ClosingPrice p,bps b where b.year = '{year}' and p.date = '{date}' and  p.id = b.id and b.val = 0;"
    sql_per_avg = f"UPDATE per bp JOIN (SELECT a1.id ,a1.date, ROUND(AVG(a1.val) over (PARTITION BY a2.cclass),2) as avg FROM per a1 ,company a2 WHERE a1.id = a2.cid and a1.date = '{date}' ) b ON bp.id = b.id and bp.date = b.date SET bp.avg = b.avg ;"
    sql_pbr_avg = f"UPDATE pbr bp JOIN (SELECT a1.id,a1.date, ROUND(AVG(a1.val) over (PARTITION BY a2.cclass),2) as avg FROM pbr a1 ,company a2 WHERE a1.id = a2.cid and a1.date = '{date}' ) b ON bp.id = b.id and bp.date = b.date SET bp.avg = b.avg ;"
    try:
        cursor.execute(sql_per)
        db.commit()
        print("per ok")
        cursor.execute(sql_per_z)
        db.commit()
        print("per z ok")
        cursor.execute(sql_per_avg)
        db.commit()
        print("per avg ok")
        logging.info(f"per update {date}")
    except:
        db.rollback()
        print("error  per ----  ",date)
    try:
        cursor.execute(sql_pbr)
        db.commit()
        print("pbr ok")
        cursor.execute(sql_pbr_z)
        db.commit()
        print("pbr z ok")
        cursor.execute(sql_pbr_avg)
        db.commit()
        print("pbr avg ok")
        logging.info(f"pbr update {date}")
    except:
        db.rollback()
        print("error  pbr ----  ",date)
    
db.close()



