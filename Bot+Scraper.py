from bs4 import BeautifulSoup
import requests
import sqlite3
import telebot
from telebot import types
import time



def getnum(text:str):
    text=str(text)
    numbers = "".join(n for n in text if n.isdigit())
    return int(numbers)




class Bot:
    TOKEN='BOT_TOKEN'
    GROUP_ID=-13243424 # GROUP ID
    def __init__(self,connection,cursors) -> None:
        self.bot = telebot.TeleBot(self.TOKEN)
        self.connection=connection
        self.cursors=cursors
    def send_message(self,text,pictures):
        restext=f"""<a href='{text['link']}'>{text['title']}</a><a>\n{text['price']}</a>"""
        medias=[]
        num=0
        for picture in pictures:
            medias.append(types.InputMediaPhoto(f"{picture}",caption = restext if num == 0 else '',parse_mode="HTML"))
            num+=1
        try:
            message= self.bot.send_media_group(self.GROUP_ID,medias)
        except Exception as ex:
            print(ex,"WAIT 10 sec.")
            time.sleep(10)
            return self.send_message(text,pictures)
        return message
    
    def sendNewInfo(self):
        advertises_info=[el for el in self.cursors.execute(f"SELECT * FROM Advertise WHERE Post='0'")]
        for advertise in advertises_info: 
            text={
                "link":advertise[0],
                "title":advertise[4],
                "price":advertise[3]
    
            }
            message=self.send_message(text,pictures=eval(advertise[5]))
            sql = "UPDATE Advertise SET Post=1, MessageID=? WHERE href=?"
            self.cursors.execute(sql, (message[0].message_id,advertise[0]))
            self.connection.commit()
    def reply_message(self,message_id,text):
        try:
            return self.bot.send_message(self.GROUP_ID,text=text,reply_to_message_id=message_id)
        except:
            time.sleep(10)
            return self.bot.send_message(self.GROUP_ID,text=text,reply_to_message_id=message_id)

class Parser:
    def __init__(self,bot,connection,cursor) -> None:
        self.bot=bot
        self.connection=connection
        self.cursors=cursor
        self.cursors.execute("CREATE TABLE IF NOT EXISTS Advertise(href TEXT PRIMARY KEY,Post,MessageID NULL,Price NULL,Title NULL,Photos Null)")
    def getSearch(self):
        resp= requests.get("https://auto.ria.com/uk/search/?indexName=auto&categories.main.id=1&brand.id[0]=79&model.id[0]=2104&country.import.usa.not=-1&price.currency=1&abroad.not=0&custom.not=1&damage.not=0&page=0&size=100")
        pagesoup=BeautifulSoup(resp.text,"lxml")
        items=pagesoup.find_all(class_="content-bar")
        for item in items:
            href=item.find(class_="m-link-ticket").get("href")
            self.cursors.execute(f"INSERT OR IGNORE INTO Advertise VALUES('{href}','0','','','','')")
        self.connection.commit()


    def getNewInfo(self):
        advertises_info=[el for el in self.cursors.execute(f"SELECT * FROM Advertise WHERE Post='0'")]
        if len(advertises_info)==0:
            print("No new posts")

        for advertise in advertises_info:
            resp=requests.get(advertise[0])
            pagesoup=BeautifulSoup(resp.text,"lxml")
            sold=len(pagesoup.find_all(class_="sold-out"))==1
            if sold:
                self.cursors.execute(f"DELETE FROM Advertise WHERE href='{advertise[0]}'")
                self.connection.commit()
                print("Car is already sold")
                continue
            
            title=pagesoup.find(class_="head").text.strip()
            price=pagesoup.find(class_="price_value").text.strip()
            pictures=pagesoup.find_all(class_="photo-620x465")[:4]
            pics_path=[]
            for picture in pictures:
                try:
                    el=picture.find("source").get('srcset')
                    pics_path.append(el)
                except:
                    pass
            sql = "UPDATE Advertise SET Price=?, Title=?, Photos=? WHERE href=?"

            # Execute the query with the parameters
            self.cursors.execute(sql, (price, title, str(pics_path), advertise[0]))
            # .cursors.execute(F"UPDATE Advertise SET Price='{price}', Title='{title}', Photos='{pics_path}' WHERE href='{advertise[0]}'")

            self.connection.commit()
    def checkOldInfo(self):
        advertises_info=[el for el in self.cursors.execute(f"SELECT * FROM Advertise WHERE Post=1")]
        for advertise in advertises_info:
         
            resp=requests.get(advertise[0])
            pagesoup=BeautifulSoup(resp.text,"lxml")
            sold=len(pagesoup.find_all(class_="sold-out"))==1
            if sold:
                self.cursors.execute(f"DELETE FROM Advertise WHERE href='{advertise[0]}'")
                self.bot.reply_message(advertise[2],f"Автомобіль продано")
                self.connection.commit()
            else:
                price=pagesoup.find(class_="price_value").text

                oldprice=getnum(advertise[3])
                newprice=getnum(price)
                if newprice!=oldprice:
                    if newprice>oldprice:    
                        self.bot.reply_message(advertise[2],f"Ціна збільшилась⬆️,тепер вона складає на {price}\nПопередня - {advertise[3]}")
                    else:
                        self.bot.reply_message(advertise[2],f"Ціна зменшилась⬇️,тепер вона складає на {price}\nПопередня - {advertise[3]}")
                    self.cursors.execute(f"UPDATE Advertise SET Price='{price}' WHERE href='{advertise[0]}'")
                    self.connection.commit()
                
                else:
                    print(f"no changes - {advertise[0]}")



if __name__=="__main__":
    connection = sqlite3.connect("data/info_db.sqlite3", timeout=10)
    cursors = connection.cursor()
    bot=Bot(connection,cursors)
    pars=Parser(bot,connection,cursors)
    while True:
        try:
            pars.checkOldInfo()
            pars.getSearch()
            pars.getNewInfo()
            bot.sendNewInfo()
            print("SLEEP 10 MIN")
            time.sleep(60*10)
        except Exception as ex:
            print(ex)
            time.sleep(10)
            

            


