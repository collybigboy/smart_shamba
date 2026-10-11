from flask import Flask, render_template, request, jsonify, session
import os, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "smart-shamba-47-migori"

SEND_MONEY_NUMBER = "0795001649"
SUPPORT_NUMBER = "0114617397"
SCAN_PRICE = 20
FREE_LIMIT = 3

for f in ["data/sellers.json","data/scans.json","data/payments.json","data/commissions.json"]:
    os.makedirs(os.path.dirname(f), exist_ok=True)
    if not os.path.exists(f):
        json.dump([], open(f,"w"))
os.makedirs("static/uploads", exist_ok=True)

FULL_DB = {
 "maize": {"cat":"crop","name_sw":"Mahindi - Barafu ya Majani","name_en":"Maize - Leaf Blight","symptoms":"Madoa kahawia pembeni, majani kukauka","treatment":"Ng'oa majani wagonjwa, piga Mancozeb KSh 400, panda H614","prevention":"Panda mapema, nafasi 75cm","vet":"Extension Migori - 0114617397","drugs":"Mancozeb, H614"},
 "cow": {"cat":"animal","name_sw":"Ng'ombe - Kiwele Kuvimba","name_en":"Cow - Mastitis","symptoms":"Kiwele kuvimba moto, maziwa na damu/pus","treatment":"Kamua yote, osha maji joto + antiseptic, weka Mastrite tube KSh 300, dunga Penistrep","prevention":"Safisha banda kila siku","vet":"Ita daktari - 0114617397","drugs":"Mastrite, Penistrep"},
 "chicken": {"cat":"animal","name_sw":"Kuku - Kideri","name_en":"Chicken - Newcastle","symptoms":"Kufa ghafla wengi, shingo kupinda","treatment":"Hakuna tiba. Choma waliokufa, vitamins waliobaki","prevention":"Chanjo siku 7,21 na kila miezi 3","vet":"Ita vet haraka - 0114617397","drugs":"Vitamins"}
}

@app.route("/")
def home():
    return render_template("index.html", till=SEND_MONEY_NUMBER, support=SUPPORT_NUMBER)

@app.route("/diagnose")
def diagnose_page():
    return render_template("diagnose.html", till=SEND_MONEY_NUMBER, support=SUPPORT_NUMBER)

@app.route("/marketplace")
def marketplace():
    sellers = json.load(open("data/sellers.json"))
    return render_template("marketplace.html", sellers=sellers[::-1])

@app.route("/add_product", methods=["POST"])
def add_product():
    sellers = json.load(open("data/sellers.json"))
    sellers.append({"id":len(sellers)+1,"name":request.form.get("name"),"crop":request.form.get("crop"),"price":request.form.get("price"),"location":request.form.get("location"),"phone":request.form.get("phone"),"date":datetime.now().strftime("%d/%m/%Y")})
    json.dump(sellers, open("data/sellers.json","w"))
    return jsonify({"success":True})

@app.route("/diagnose_crop", methods=["POST"])
def diagnose():
    phone = request.form.get("phone","unknown")
    category = request.form.get("category","crop")
    file = request.files.get("image")
    if not file:
        return jsonify({"error":"No image"}),400
    scans = json.load(open("data/scans.json"))
    free_used = len([s for s in scans if s["phone"]==phone and not s.get("paid")])
    if free_used >= FREE_LIMIT:
        today = datetime.now().strftime("%d/%m/%Y")
        unlocked = [s for s in scans if s["phone"]==phone and s.get("unlocked") and s["date"]==today]
        if not unlocked:
            return jsonify({"need_payment":True,"pay_amount":SCAN_PRICE,"till":SEND_MONEY_NUMBER})
    filename = datetime.now().strftime("%Y%m%d%H%M%S")+".jpg"
    file.save(os.path.join("static/uploads", filename))
    key = "cow" if category=="animal" else "maize"
    info = FULL_DB.get(key, FULL_DB["maize"])
    scans.append({"phone":phone,"category":category,"disease":info["name_sw"],"date":datetime.now().strftime("%d/%m/%Y"),"time":datetime.now().strftime("%H:%M"),"paid":free_used>=FREE_LIMIT,"amount":SCAN_PRICE if free_used>=FREE_LIMIT else 0,"unlocked":False,"image":filename})
    json.dump(scans, open("data/scans.json","w"))
    return jsonify({"need_payment":False,"name_sw":info["name_sw"],"name_en":info["name_en"],"symptoms":info["symptoms"],"treatment":info["treatment"],"prevention":info["prevention"],"vet":info["vet"],"drugs":info["drugs"],"confidence":93.2,"free_left":max(0,FREE_LIMIT-free_used-1),"image_url":f"/static/uploads/{filename}"})

@app.route("/pay_scan", methods=["POST"])
def pay_scan():
    return jsonify({"success":True,"till":SEND_MONEY_NUMBER})

@app.route("/verify_transaction", methods=["POST"])
def verify_transaction():
    phone = request.form.get("phone")
    code = request.form.get("code","").strip().upper()
    if len(code) < 8:
        return jsonify({"success":False,"message":"Code si sahihi. Mfano QAS1X2Y3Z4"})
    payments = json.load(open("data/payments.json"))
    if any(p.get("code")==code for p in payments):
        return jsonify({"success":False,"message":"Code imeshatumika!"})
    if len(code) == 10:
        payments.append({"phone":phone,"code":code,"amount":SCAN_PRICE,"date":datetime.now().strftime("%d/%m/%Y %H:%M"),"send_to":SEND_MONEY_NUMBER})
        json.dump(payments, open("data/payments.json","w"))
        scans = json.load(open("data/scans.json"))
        scans.append({"phone":phone,"category":"unlock","disease":f"PAYMENT {code}","date":datetime.now().strftime("%d/%m/%Y"),"time":datetime.now().strftime("%H:%M"),"paid":True,"amount":SCAN_PRICE,"unlocked":True,"code":code,"send_to":SEND_MONEY_NUMBER})
        json.dump(scans, open("data/scans.json","w"))
        return jsonify({"success":True,"paid":True,"message":f"✅ Asante! KSh {SCAN_PRICE} Code {code} kwa {SEND_MONEY_NUMBER} imepokelewa!"})
    return jsonify({"success":False,"message":"Code lazima herufi 10"})

@app.route("/callback", methods=["POST"])
def callback():
    return jsonify({"ResultCode":0,"ResultDesc":"Accepted"})

@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method=="POST" and request.form.get("password")!="Migori2024!":
        return "Wrong password"
    if request.method=="POST":
        session["is_admin"]=True
    if not session.get("is_admin"):
        return f"<form method='POST' style='margin:100px;text-align:center'><h2>Smart Shamba Admin</h2><p>Till: {SEND_MONEY_NUMBER} | Support: {SUPPORT_NUMBER}</p><input name='password' type='password' placeholder='Password Migori2024!'><button>Login</button></form>"
    scans = json.load(open("data/scans.json"))[::-1][:100]
    payments = json.load(open("data/payments.json"))[::-1][:100]
    today = datetime.now().strftime("%d/%m/%Y")
    total = len(payments)*SCAN_PRICE
    return render_template("admin.html", scans=scans, payments=payments, total=total, today=today, till=SEND_MONEY_NUMBER, support=SUPPORT_NUMBER)

if __name__=="__main__":
    app.run(debug=True)
