from flask import Flask, render_template, request, redirect, session, url_for, jsonify,flash
import sqlite3,io,base64
from datetime import datetime
from collections import Counter
import matplotlib,math
matplotlib.use('Agg')   
import matplotlib.pyplot as pt
app = Flask(__name__)
app.secret_key = 'secr  et-key'

@app.route('/')
def home():
    return render_template('welcome.html')
@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        user_name=request.form['user_name']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        mobile_number = request.form['mobile_number']
        driving_licese = request.form['driving_licese']

        conn = sqlite3.connect('parkingvehicle.db')
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO users (user_name,email, password, full_name, address,mobile_number, pin_code,driving_licese)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_name,email, password, full_name, address,mobile_number, pin_code,driving_licese))
            conn.commit()
        except sqlite3.IntegrityError:
            return "User already exists!"
        conn.close()

        return redirect('/login')
    return render_template('register.html')
@app.route('/login',methods=['GET','POST'])
def login_user():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('parkingvehicle.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            if user:
                session['user_id'] = user[0]  
                session['user_name'] = user[3] 
                session['email']=user[1] 
                return redirect('/user_dashboard')

            return redirect('/user_dashboard')
        else:
            return "Invalid credentials!"
    return render_template('login.html')
@app.route('/user_dashboard', methods=['GET', 'POST'])
def user_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    

    user_id = session['user_id']
    
    conn_user = sqlite3.connect('parkingvehicle.db')
    c = conn_user.cursor()

    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    user_name = user[1]
    c.execute("SELECT * FROM slots")
    row=c.fetchall()
    for i in row:
        b=i[0]
        d=i[3]
        x=update_avaiable(b)
        c.execute("""
        UPDATE slots
        SET available = ?
        WHERE id=?
    """, (x,b))
    conn_user.commit()
    c.execute("""
        SELECT id, user_name, vehicle_number, entry_time, exit_time, status, slot_address
        FROM bookings
        WHERE user_name = ?
        ORDER BY entry_time DESC
        LIMIT 5;
    """, (user_name,))
    row = c.fetchall()

    c.execute("SELECT slot_name, slot_address, pincode,total_lot,id ,available FROM slots")
    slots = c.fetchall()

    if request.method == 'POST':
        print("this is to check",request.method)
        query = request.form.get('query')
        if not query:  
            return render_template('user_dashboard.html', 
                                 error="Please enter a search term")

        matched_slots = []
        for slot in slots:
            slot_name, slot_address, pincode ,total_lot,id,available= slot
            if query.lower() in slot_name.lower() or query.lower() in slot_address.lower() or query.lower() in str(pincode)or query.lower() in str(total_lot)or query.lower() in str(id)or query.lower() in str(available):
                matched_slots.append(slot)
       
            print(matched_slots)    

        return render_template('user_dashboard.html', user_name=user_name, row=row, matched_slots=matched_slots,query=query)

    conn_user.close()

    return render_template('user_dashboard.html', user_name=user_name, row=row)

@app.route('/logout')
def logout():
    return redirect('/')
@app.route('/about')
def about():
    if 'user_id' not in session:
        return redirect('/login')
    user_id=session['user_id']
    conn_user=sqlite3.connect('parkingvehicle.db')
    c= conn_user.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user_name=c.fetchone()[1]
    
    conn_user.close()

    return render_template("about.html",user_name=user_name)
@app.route('/contact')
def contact():
    if 'user_id' not in session:
        return redirect('/login')
    user_id=session['user_id']
    conn_user=sqlite3.connect('parkingvehicle.db')
    c= conn_user.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user_name=c.fetchone()[1]
    
    conn_user.close()

    return render_template("contact.html",user_name=user_name)
@app.route('/edit_profile',methods=['GET','POST'])
def editprofile():
    if 'user_id' not in session:
        return redirect('/login')
    user_id=session['user_id']
    conn_user=sqlite3.connect('parkingvehicle.db')
    c= conn_user.cursor()

    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user_name=c.fetchone()[1]
    conn_user.close()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with sqlite3.connect('parkingvehicle.db') as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE users
                SET  email = ?, password = ?
                WHERE id = ?
            """, ( email, password, user_id))
            conn.commit()
            
            flash('Profile updated successfully!', 'success')
        return redirect('/user_dashboard')
    return render_template('edit_profile.html', user_name=user_name)

@app.route('/user_booking', methods=['GET', 'POST'])
def user_booking():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    print("user side booking chcek",user_id)

    with sqlite3.connect('parkingvehicle.db') as conn:
        c = conn.cursor()

        c.execute("SELECT user_name, mobile_number, driving_licese FROM users WHERE id=?", (user_id,))
        user = c.fetchone()
        if not user:
            flash("User not found", "error")
            return redirect('/login')

        user_name, mobile_number, driving_licese = user

        c.execute("SELECT id, slot_name, slot_address FROM slots")
        all_slots = c.fetchall()

        if request.method == 'POST':
            print("RAW FORM DATA:", request.form)
            print("HEADERS:", request.headers)

            vehicle_number = request.form.get('vehicle_number')
            lots = request.form.get('lot')
            lot=int(lots)


            if not vehicle_number or not lot:
                flash('All fields are required', 'error')
                return redirect(url_for('user_booking'))

            status = 1
            entry_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            exit_time = None
            cost = 0.0

            slot_id = session.get('selected_slot_id')
            if not slot_id:
                flash("No slot selected", "error")
                return redirect('/user_dashboard')

            c.execute("SELECT slot_address FROM slots WHERE id = ?", (slot_id,))
            slot_info = c.fetchone()
            if not slot_info:
                flash("Invalid slot selected", "error")
                return redirect('/user_dashboard')

            slot_address = slot_info[0]

            c.execute("""
                SELECT 1 FROM bookings
                WHERE LOWER(vehicle_number) = ? AND status = 1
            """, (vehicle_number.lower(),))
            if c.fetchone():
                flash("This vehicle already has an active booking!", "warning")
                return redirect('/already_booked')

            c.execute("""
                INSERT INTO bookings (
                    user_name, mobile_number, driving_licese, entry_time, exit_time,
                    lot, vehicle_number, status, cost, slot_address, slot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_name, mobile_number, driving_licese,
                  entry_time, exit_time, lot, vehicle_number, status, cost, slot_address, slot_id))

            c.execute("""
                SELECT user_name, vehicle_number, entry_time
                FROM bookings
                WHERE lot = ? AND slot = ?
                ORDER BY id DESC LIMIT 1
            """, (lot, slot_id))
            latest_booking = c.fetchone()

            if latest_booking:
                latest_user, latest_vehicle, latest_entry = latest_booking

                c.execute("""
                    UPDATE lots
                    SET 
                        user_name = ?,
                        vehicle_number = ?,
                        entry_time = ?,
                        occupied = 1
                    WHERE lot_no = ? AND slot_id = ?
                """, (latest_user, latest_vehicle, latest_entry, lot, slot_id))

                c.execute("""
                    UPDATE lots
                    SET available_lot = (
                        SELECT COUNT(*) FROM lots
                        WHERE slot_id = ? AND occupied = 0
                    )
                    WHERE slot_id = ?
                """, (slot_id, slot_id))

            conn.commit()
            flash('Booking successful!', 'success')
            return redirect('/user_dashboard')
        slot_id = session.get('selected_slot_id')
        c.execute("select lot_no from lots where slot_id=? and occupied=0", (slot_id,))
        
        totall=c.fetchall()
        print("this is just to check ")
        
        return render_template('user_booking.html',totall=totall)


@app.route('/already_booked')
def already_booked():
    return render_template('already_booked.html')

@app.route('/admin_slot', methods=['GET', 'POST'])
def admin_slot():
    if request.method == 'POST':
        slot_name = request.form['slot_name']
        slot_address = request.form['slot_address']
        pincode = request.form['pincode']
        total_lot = int(request.form['total_lot'])
        cost=int(request.form['cost'])
        print(cost)
        conn = sqlite3.connect('parkingvehicle.db')
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO slots (slot_name, slot_address,pincode, total_lot, cost)
                VALUES (?, ?, ?, ?, ?)
            """, (slot_name, slot_address,pincode, total_lot,cost))
            slot_id = c.lastrowid
            for i in range(1, total_lot + 1):
                c.execute("""
                    INSERT INTO lots (slot_id, lot_no, available_lot, occupied, price)
                    VALUES (?, ?, ?, 0, ?)
                """, (slot_id, i, 1, cost))




            conn.commit()
            conn.close()
            flash('Slot added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Slot already exists!', 'danger')
        return redirect('/admin_dashboard')
        
        

    return render_template('admin_slot.html')
@app.route('/lot_booking')
def lot_booking():
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    conn_user = sqlite3.connect('parkingvehicle.db')
    c = conn_user.cursor()
    c.execute("SELECT user_name,vehicle_number,lot,status,entry_time FROM bookings WHERE id = ?", (user_id,))
    r=c.fetchall()
    
    user_name = r[0][0] if r else "User"
    vehicle_number = r[0][1] if r else "No Vehicle"
    lot = r[0][2] if r else "No Lot"
    status = r[0][3] if r else "No Status"
    entry_time = r[0][4] if r else "No Entry Time"
    c.execute("""
    INSERT INTO lots (user_name, vehicle_number, lot, status, entry_time)
      VALUES(?, ?, ?, ?, ?)        
 """)(user_name, vehicle_number, lot, status, entry_time)






@app.route('/summary')
def summary():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    conn_user = sqlite3.connect('parkingvehicle.db')
    c = conn_user.cursor()
    c.execute("SELECT user_name FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()

    if not result:
        conn_user.close()
        return "User not found", 404

    user_name = result[0]
    c.execute("SELECT * FROM bookings WHERE user_name = ?", (user_name,))
    user_data = c.fetchall()
    conn_user.close()
    for i in user_data:
        print(i)
    print(" ")
    
    v_no1=[r[4]for r in user_data]
    v_no2=[r[11]for r in user_data]
    f1 = (Counter(v_no1))
    f2 = Counter(v_no2)
    print("this is the data of f1",f1)
        
    a=(list(f1.keys()))
    b=(list(f1.values()))
    c=(list(f2.keys()))
    d=(list(f2.values()))
    fig, (ax1, ax2) = pt.subplots(1, 2, figsize=(10, 4))

    ax1.bar(a, b, color='blue')
    ax1.set_title('Vehicle Number Count')
    ax1.set_xlabel('Vehicle Number')
    ax1.set_ylabel('Count')
    ax2.bar(c, d, color='green')
    ax2.set_title('Slot Address Count')
    ax2.set_xlabel('Slot Address')
    ax2.set_ylabel('Count')
    img = io.BytesIO()
    pt.tight_layout()
    fig.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    pt.close(fig)




    return render_template('summary.html', user_data=user_data,plot_url=plot_url)
@app.route('/admin_login', methods=['GET', 'POST'])   
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('parkingvehicle.db')
        c = conn.cursor()
        c.execute("SELECT * FROM admin WHERE email=? AND password=?", (email, password)) 
        admin = c.fetchone()
        conn.close()
        if admin:
            session['admin_id'] = admin[0]  
            session['admin_name'] = admin[1] 
            return redirect('/admin_dashboard')
        else:
            return "Invalid credentials!"
    return render_template('admin_login.html')   
@app.route('/admin_dashboard')
def admin_dashooard():
    if 'admin_id' not in session:
        return redirect('/admin_login')
    
    conn = sqlite3.connect('parkingvehicle.db')
    conn.row_factory = sqlite3.Row  # So you can use column names like row['id']
    c = conn.cursor()

    # Fetch all slots
    c.execute("SELECT * FROM slots")
    slots = c.fetchall()

    slot_data = []

    for slot in slots:
        slot_id = slot['id']
        total_lot = slot['total_lot']
        
        # Update available lots for this slot
        x = update_avaiable(slot_id)
        c.execute("UPDATE slots SET available = ? WHERE id = ?", (x, slot_id))
        conn.commit()

        # Get all lots for this slot
        c.execute("SELECT * FROM lots WHERE slot_id = ? ORDER BY lot_no", (slot_id,))
        lots = c.fetchall()

        # Append to slot_data
        slot_data.append({
            'slot': slot,
            'lots': lots
        })

    conn.close()

    return render_template('admin_dashboard.html', slot_data=slot_data)



@app.route('/slot_set', methods=['POST'])
def set_slot_session():
    if 'user_id' not in session:
        return redirect('/login')
    
    slot_id = request.form.get('slot_id')
    if not slot_id:
        flash('No slot selected', 'error')
        return redirect('/user_dashboard')
    
    session['selected_slot_id'] = slot_id
    print("this checks the slot user is booking",slot_id)
    
    return redirect('/user_booking')
@app.route('/user/release/<int:booking_id>')
def dec_count(booking_id):
    conn = sqlite3.connect('parkingvehicle.db')
    c = conn.cursor()
    c.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    t = c.fetchall()
    st_id=t[0][7]
    print(st_id)
    lt_id=t[0][8]
    occ=0
    sts=0
    x=earning(booking_id)
    exit=x[0]
    c.execute("SELECT * FROM slots WHERE id = ?", (st_id,))
    print(st_id)
    y=c.fetchall()
    print(y)
    cost=y[0][4]
    dur=x[1]
    earnings=cost*dur
    tot_ear=y[0][6]
    print('this is total earning of slot id',tot_ear)
    

    if y[0][6] is not None:
        tot_ear+=earnings
        c.execute("""
        UPDATE slots
        SET total_earning = ?
        WHERE id=?
    """, (tot_ear,st_id))
        conn.commit()
    else:
        c.execute("""
        UPDATE slots
        SET total_earning = ?
        WHERE id=?
    """, (earnings,st_id))
        conn.commit()

    

    c.execute("""
    UPDATE lots
    SET occupied = ?, exit_time = ?,earning= ?
    WHERE lot_no = ? AND slot_id = ?
""", (occ,exit,earnings, lt_id, st_id))
    conn.commit()

    c.execute("""
    UPDATE bookings
    SET status = ?, exit_time = ?
    WHERE id=?
""", (sts,exit, booking_id))
    conn.commit()

    conn.close()
    


    return redirect('/user_dashboard')
def earning(booking_id):
    conn=sqlite3.connect('parkingvehicle.db')
    c=conn.cursor()
    c.execute("SELECT * FROM bookings WHERE id = ?",(booking_id,))
    a=c.fetchall()
    
    
    fmt = '%Y-%m-%d %H:%M:%S'
    entry_time=a[0][5]
    exit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = datetime.strptime(entry_time, fmt)
    exit = datetime.strptime(exit_time, fmt)
    d=(exit-entry)/3600
    h=d.total_seconds()
    return(exit_time,h)

@app.route('/lot_view/<int:lot>/<int:slot>')
def lot_view(lot,slot):
    if 'admin_id' not in session:     
        return redirect('/admin_login')
    
    print(lot,slot)
    conn=sqlite3.connect('parkingvehicle.db')
    c=conn.cursor()
    c.execute("SELECT * FROM lots WHERE id =?",(lot,))
    lots=c.fetchone()
    user=lots[9]
    print(user)
    c.execute("SELECT * FROM users WHERE user_name = ?",(user,))
    name=c.fetchone()
    add=name[5]
    lisc=name[8]
    print('hello this is it',lots,add,lisc  )
    conn.close()
    
    
    
    return render_template('lot_view.html',lots=lots,add=add,lisc=lisc)
def update_avaiable(slot):
    conn=sqlite3.connect('parkingvehicle.db')
    c=conn.cursor()
    c.execute("SELECT * FROM slots WHERE id = ?",(slot,))
    b=c.fetchall()
    total=b[0][3]
    print(total)

    c.execute("SELECT * FROM lots WHERE slot_id = ?",(slot,))
    a=c.fetchall()
    count=0
    for i in a:
        
        if i[7]==1:
            
            count+=1
        print(count)
        remain=total-count
    return remain
        
@app.route('/edit_slot/<slot_id>', methods=['GET', 'POST'])
def edit_slot(slot_id):
    if 'admin_id' not in session:
        return redirect('/admin_login')

    conn = sqlite3.connect('parkingvehicle.db')
    c = conn.cursor()

    if request.method == 'POST':
        slot_name = request.form['slot_name']
        total_lot = int(request.form['total_lot'])
        cost = int(request.form['cost'])

        c.execute("SELECT COUNT(*) FROM lots WHERE slot_id = ?", (slot_id,))
        current_lot_count = c.fetchone()[0]

        c.execute("""
            UPDATE slots
            SET slot_name = ?, total_lot = ?, cost = ?
            WHERE id = ?
        """, (slot_name, total_lot, cost, slot_id))

        c.execute("""
            UPDATE lots
            SET price = ?
            WHERE slot_id = ?
        """, (cost, slot_id))

        if total_lot > current_lot_count:
            for i in range(current_lot_count + 1, total_lot + 1):
                c.execute("""
                    INSERT INTO lots (slot_id, lot_no, available_lot, occupied, price)
                    VALUES (?, ?, ?, 0, ?)
                """, (slot_id, i, 1, cost))

        elif total_lot < current_lot_count:
            for i in range(current_lot_count, total_lot, -1):
                c.execute("""
                    SELECT occupied FROM lots
                    WHERE slot_id = ? AND lot_no = ?
                """, (slot_id, i))
                row = c.fetchone()

                if row and row[0] == 0:
                    c.execute("""
                        DELETE FROM lots
                        WHERE slot_id = ? AND lot_no = ?
                    """, (slot_id, i))
                else:
                    flash(f"Lot {i} is occupied and cannot be deleted.", "warning")

        conn.commit()
        flash("Slot updated successfully.", "success")
        return redirect('/admin_dashboard')

    c.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
    ed = c.fetchall()
    conn.close()

    return render_template("admin_adit_slot.html",ed=ed)
@app.route('/delete_slot/<slot_id>', methods=['GET', 'POST'])
def del_slot(slot_id):
    conn = sqlite3.connect('parkingvehicle.db')
    c = conn.cursor()
    c.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
    conn.commit()
    conn.close()
    return redirect('/admin_dashboard')

@app.route('/view_registered_users')
def view_register_user():
    conn=sqlite3.connect('parkingvehicle.db')
    c=conn.cursor()
    c.execute("SELECT * FROM users")
    users=c.fetchall()
    print(users)
    conn.close()
    return render_template('view_registered_user.html',users=users)
@app.route('/admin_summary')
def admin_summary():
    conn=sqlite3.connect('parkingvehicle.db')
    c=conn.cursor()
    c.execute("SELECT * FROM slots ")
    z=c.fetchall()
    avail=[]
    add=[]
    cos=[]
    tot=[]

    for i in z:
        avail.append(i[7])
    print(avail)
    for i in z:
        add.append(i[2])
    print(add)
    for i in z:
        cos.append(i[6])
    print(cos)
    for i in z:
        tot.append(i[3])
    print(tot)
    cos1 = [0 if (v is None or (isinstance(v, float) and math.isnan(v))) else v for v in cos]


    fig, ((ax1, ax2), (ax3, ax4)) = pt.subplots(2, 2, figsize=(12, 8))  


    
    ax1.pie(tot, labels=add, autopct='%1.1f%%', startangle=140)
    ax1.set_title('Total lot in each slot')

    
    ax2.pie(cos1, labels=add, autopct='%1.1f%%', colors=['pink',"lightblue" ,'lightgreen'], startangle=90)
    ax2.set_title('Earning per Slot ')

    
    ax3.bar(add, avail, color='skyblue')
    ax3.set_title('Current lot available per slot')
    ax3.set_xlabel('Parking Lot')
    ax3.set_ylabel('Vehicles')
    ax4.axis('off')
    
    img = io.BytesIO()
    pt.tight_layout()
    fig.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    pt.close(fig)

    return render_template('admin_summary.html', plot_url=plot_url)
    
@app.route('/search',methods=['GET','POST'])
def search():
    conn=sqlite3.connect('parkingvehicle.db')
    c=conn.cursor()
    c.execute("SELECT * FROM bookings")
    uniq=c.fetchall()
    reqs=[]
    query=''
    
    
    if request.method == 'POST':
        print("this is to check",request.method)
        query = request.form.get('query')
        print(query)
        if not query:  
            return render_template('search.html', 
                                 error="Please enter a search term")
        
        for sloty in uniq:
           
                print(sloty[9])
                user_name=sloty[1]
                slot_address=sloty[11]
                
                if query.lower() in user_name.lower() or query.lower() in slot_address.lower():

                    reqs.append(sloty)
        conn.close()
  
    
        return render_template('search.html',reqs=reqs,query=query)

    conn.close()

    return render_template('search.html', reqs=reqs,query=query)
@app.route('/cost')
def cost():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    with sqlite3.connect('parkingvehicle.db') as conn:
        
        c = conn.cursor()
        c.execute("SELECT user_name FROM users WHERE id = ?", (user_id,))
        result = c.fetchone()
        user_name=result[0]
        c.execute("select l.slot_id,l.lot_no,l.vehicle_number,l.entry_time,l.exit_time,l.earning,s.slot_address,s.slot_name from lots as l join slots as s on l.slot_id=s.id where l.user_name=? order by l.entry_time desc",(result[0],))
        zdata = c.fetchall()
        for i in zdata:
            print(i)

    

    
    
   
    return render_template('cost.html',zdata=zdata,user_name=user_name)
from flask import request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io, sqlite3
from datetime import datetime

@app.route('/download_bill')
def download_bill():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    mode = request.args.get("mode")
    count = request.args.get("count", type=int)

    with sqlite3.connect("parkingvehicle.db") as conn:
        c = conn.cursor()

        # Get username
        c.execute("SELECT user_name FROM users WHERE id=?", (user_id,))
        user_row = c.fetchone()
        if not user_row:
            return "User not found", 404
        user_name = user_row[0]

        # Base query
        query = """SELECT l.slot_id, l.lot_no, l.vehicle_number,
                          l.entry_time, l.exit_time, l.earning,
                          s.slot_address, s.slot_name
                   FROM lots AS l 
                   JOIN slots AS s ON l.slot_id = s.id
                   WHERE l.user_name=?
                   ORDER BY l.entry_time DESC"""
        
        if mode == "last":
            query += " LIMIT 1"
            c.execute(query, (user_name,))
        elif mode == "last_n" and count:
            query += " LIMIT ?"
            c.execute(query, (user_name, count))
        else:  # default = all
            c.execute(query, (user_name,))

        records = c.fetchall()

    if not records:
        return "No records found", 404

    # Prepare PDF
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle("TitleStyle", parent=styles['Title'], alignment=1, fontSize=20, spaceAfter=20)
    normal_bold = ParagraphStyle("NormalBold", parent=styles['Normal'], fontSize=11, leading=14, spaceAfter=6, fontName="Helvetica-Bold")

    # Header
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Paragraph(f"Invoice Number: {1000+user_id}", styles['Normal']))
    elements.append(Paragraph(f"Date of Issue: {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
    elements.append(Spacer(1, 15))

    # Seller & Buyer info
    seller_buyer_data = [
        ["Seller:", "Vehicle Management pvt:"],
        ["Smart Parking System", f"{user_name}"],
        ["123 Parking Lane, City, Country", "Registered User"],
    ]
    sb_table = Table(seller_buyer_data, colWidths=[260, 260])
    sb_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(sb_table)
    elements.append(Spacer(1, 25))

    # Bill details table
    data = [["Sl.No", "Slot Name", "Slot Address", "Entry Time", "Exit Time", "Vehicle No", "Cost (Rs)"]]
    total_cost = 0
    for idx, row in enumerate(records, 1):
        slot_name, slot_address, entry, exit_time, vehicle, earning = row[7], row[6], row[3], row[4], row[2], row[5]
        try:
            earning = float(earning)
        except:
            earning = 0
        total_cost += earning
        data.append([
            idx,
            slot_name,
            slot_address,
            str(entry),
            str(exit_time),
            vehicle,
            f"{earning:.2f}"
        ])
        seller_buyer_data = [
        ["Seller:", "Vehicle Management pvt Ltd:"],
        ["Smart Parking System", f"{user_name}"],
        ["123 Parking Lane, City, Country", "Registered User"],
    ]

    # Total row
    data.append(["", "", "", "", "", "Total", f"{total_cost:.2f}"])

    table = Table(data, repeatRows=1, colWidths=[40, 70, 120, 90, 90, 80, 70])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -2), colors.whitesmoke),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))

    elements.append(table)
    # After elements.append(table)

    elements.append(Spacer(1, 40))  
    elements.append(Paragraph("Digital Signature", normal_bold))  
    elements.append(Paragraph("Department Head"))
    elements.append(Paragraph("Shri Akshay jha ", normal_bold))
        # Add signature image (make sure you have a static/elon_signature.png file)
    

    doc.build(elements)
    pdf_buffer.seek(0)

    return send_file(pdf_buffer, as_attachment=True,
                     download_name="invoice.pdf", mimetype="application/pdf")

@app.route('/bill_options')
def bill_options():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    with sqlite3.connect('parkingvehicle.db') as conn:
        c = conn.cursor()

        # count how many bills exist for this user
        c.execute("""SELECT COUNT(*) 
                     FROM lots 
                     WHERE user_name = (SELECT user_name FROM users WHERE id = ?)""", (user_id,))
        total_records = c.fetchone()[0]

    return render_template('bill_options.html', total_records=total_records)


if __name__ == '__main__':
    app.run(debug=True)
