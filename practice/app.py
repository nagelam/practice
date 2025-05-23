from flask import Flask, request, render_template, redirect, url_for, send_file, flash
import os
import io
import csv

app = Flask(__name__)
app.secret_key = 'secretkey'
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Глобальное хранилище контактов 
contacts = []

def parse_vcf(file_content):
    """
    Простейший парсер .vcf файла.
    Принимает содержимое файла в виде строки и возвращает список контактов.
    Каждый контакт представляется как словарь с полями: family, given, full_name, tel_work, tel_home.
    """
    parsed_contacts = []
    lines = file_content.splitlines()
    current_contact = {}
    for line in lines:
        if line.startswith("BEGIN:VCARD"):
            current_contact = {}
        elif line.startswith("END:VCARD"):
            parsed_contacts.append(current_contact)
        else:
            if ":" in line:
                key, value = line.split(":", 1)
                if key.startswith("N"):
                    # Формат: Фамилия;Имя;...
                    parts = value.split(";")
                    current_contact["family"] = parts[0] if len(parts) > 0 else ""
                    current_contact["given"] = parts[1] if len(parts) > 1 else ""
                elif key.startswith("TEL"):
                    # Различение типов телефонов по параметрам
                    if "WORK" in key.upper():
                        current_contact["tel_work"] = value
                    elif "HOME" in key.upper():
                        current_contact["tel_home"] = value
                    else:
                        current_contact.setdefault("tel", value)
                elif key.startswith("FN"):
                    current_contact["full_name"] = value
                else:
                    current_contact[key] = value
    return parsed_contacts

def generate_vcf(contacts):
    """
    Генерация .vcf файла из списка контактов.
    """
    output = ""
    for contact in contacts:
        output += "BEGIN:VCARD\nVERSION:3.0\n"
        if "family" in contact or "given" in contact:
            family = contact.get("family", "")
            given = contact.get("given", "")
            output += f"N:{family};{given};;;\n"
        if "full_name" in contact:
            output += f"FN:{contact['full_name']}\n"
        if "tel_work" in contact:
            output += f"TEL;TYPE=WORK:{contact['tel_work']}\n"
        if "tel_home" in contact:
            output += f"TEL;TYPE=HOME:{contact['tel_home']}\n"
        output += "END:VCARD\n"
    return output

def generate_csv(contacts):
    """
    Генерация CSV из списка контактов.
    """
    output = io.StringIO()
    fieldnames = ['family', 'given', 'full_name', 'tel_work', 'tel_home']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for contact in contacts:
        writer.writerow({field: contact.get(field, "") for field in fieldnames})
    return output.getvalue()

@app.route('/', methods=['GET', 'POST'])
def index():
    global contacts
    if request.method == 'POST':
        if 'vcf_file' not in request.files:
            flash('Файл не выбран')
            return redirect(request.url)
        file = request.files['vcf_file']
        if file.filename == '':
            flash('Файл не выбран')
            return redirect(request.url)
        if file:
            file_content = file.read().decode('utf-8')
            contacts = parse_vcf(file_content)
            return redirect(url_for('list_contacts'))
    return render_template('index.html')

@app.route('/contacts')
def list_contacts():
    global contacts
    search = request.args.get('search', '')
    filtered_contacts = contacts
    if search:
        filtered_contacts = [c for c in contacts if search.lower() in c.get("full_name", "").lower() or
                             search.lower() in c.get("given", "").lower() or
                             search.lower() in c.get("family", "").lower()]
    return render_template('contacts.html', contacts=filtered_contacts, search=search)

@app.route('/edit/<int:index>', methods=['GET', 'POST'])
def edit_contact(index):
    global contacts
    if index < 0 or index >= len(contacts):
        flash("Контакт не найден")
        return redirect(url_for('list_contacts'))
    contact = contacts[index]
    if request.method == 'POST':
        contact['family'] = request.form.get('family', '')
        contact['given'] = request.form.get('given', '')
        contact['full_name'] = request.form.get('full_name', '')
        contact['tel_work'] = request.form.get('tel_work', '')
        contact['tel_home'] = request.form.get('tel_home', '')
        contacts[index] = contact
        return redirect(url_for('list_contacts'))
    return render_template('edit_contact.html', contact=contact, index=index)

@app.route('/delete/<int:index>', methods=['POST'])
def delete_contact(index):
    global contacts
    if 0 <= index < len(contacts):
        contacts.pop(index)
    return redirect(url_for('list_contacts'))

@app.route('/add', methods=['GET', 'POST'])
def add_contact():
    global contacts
    if request.method == 'POST':
        new_contact = {
            'family': request.form.get('family', ''),
            'given': request.form.get('given', ''),
            'full_name': request.form.get('full_name', ''),
            'tel_work': request.form.get('tel_work', ''),
            'tel_home': request.form.get('tel_home', '')
        }
        contacts.append(new_contact)
        return redirect(url_for('list_contacts'))
    return render_template('edit_contact.html', contact={}, index=len(contacts))

@app.route('/export/vcf')
def export_vcf():
    global contacts
    vcf_data = generate_vcf(contacts)
    return send_file(io.BytesIO(vcf_data.encode('utf-8')),
                     as_attachment=True,
                     download_name='contacts.vcf',
                     mimetype='text/vcard')

@app.route('/export/csv')
def export_csv():
    global contacts
    csv_data = generate_csv(contacts)
    return send_file(io.BytesIO(csv_data.encode('utf-8')),
                     as_attachment=True,
                     download_name='contacts.csv',
                     mimetype='text/csv')

if __name__ == '__main__':
    app.run(debug=True)
