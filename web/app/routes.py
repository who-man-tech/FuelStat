# Данные файл содержит в себе функции для отображения страниц, по
# указанным путям


from app import flsk
from flask import render_template, flash, redirect, url_for, request
from app.forms import LoginForm, NavigationForm, TableRowForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from werkzeug.urls import url_parse
import sqlite3

# TODO: Добавить проверку введенных данных в формы новой заправки


@flsk.route("/index", methods=["GET", "POST"])
@login_required # Проверяем авторизовался ли пользователь
def index():
    db = sqlite3.connect("../data/database.db")
    fuel_data = db.execute("SELECT id, name FROM fuel ORDER BY id")
    navig_data = db.execute("SELECT CAST(id as TEXT), name FROM fuel")

    navig_form = NavigationForm()
    navig_form.names.choices = navig_data

    row_form = TableRowForm()

    db.execute("DROP VIEW IF EXISTS vtrans")
    db.execute("""CREATE VIEW vtrans AS SELECT
                  t.id, t.fuel_id, t.dtime, t.odometer, f.name, t.amount
                  FROM trans t, fuel f WHERE t.fuel_id = f.id
                  ORDER BY t.dtime""")

    if row_form.validate_on_submit() or navig_form.validate_on_submit():
        if row_form.save.data:
            db.execute("UPDATE trans" +
                       " SET dtime = '" + str(row_form.date.data) + "'" +
                       ", odometer = " + str(row_form.odometer.data) +
                       ", fuel_id = " + str(row_form.fuel_station.data) +
                       ", amount = " + str(row_form.gallon_count.data) + 
                       " WHERE id = " + str(row_form.id.data))
            db.commit()
        elif navig_form.allow.data:
            command = ("""CREATE VIEW vtrans AS SELECT
                          t.id,  t.fuel_id, t.dtime, t.odometer, f.name, t.amount
                          FROM trans t, fuel f WHERE t.fuel_id = f.id""" +
                       " AND t.dtime > '" + str(navig_form.start_date.data) + "'" +
                       " AND t.dtime < '" + str(navig_form.end_date.data) + "'")
            if len(navig_form.names.data) == 1:
                command += " AND t.fuel_id == " + str(navig_form.names.data[0])
            elif len(navig_form.names.data) != 0:
                command += " AND t.fuel_id in " + str(tuple(navig_form.names.data))
            command += " ORDER BY dtime"
            db.execute("DROP VIEW IF EXISTS vtrans")
            db.execute(command)
        elif row_form.delete.data:
            if row_form.id.data is not None:
                print("deleting")
                db.execute("DELETE FROM trans WHERE id = " + str(row_form.id.data))
                db.commit()
        elif row_form.add.data:
            db.execute("INSERT INTO trans(dtime, odometer, fuel_id, amount) VALUES (" +
                       "'" + str(row_form.date.data) + "'" +
                       ", " + str(row_form.odometer.data) + 
                       ", " + str(row_form.fuel_station.data) +
                       ", " + str(row_form.gallon_count.data) + ")")
            db.commit()

    trans_data = db.execute("""SELECT id, fuel_id, dtime, odometer, name, amount
                               FROM vtrans""")

    return render_template("index.html",
                           trans_data=trans_data,
                           fuel_data=fuel_data,
                           navig_form=navig_form,
                           row_form=row_form)



@flsk.route("/", methods=["GET", "POST"])
@flsk.route("/login", methods=["GET", "POST"])
def login():
    # При входе на сайт, пользователь сразу переходит к странице
    # авторизации.
    # Он вводит свой логин и пароль, а так как пользователь у нас один,
    # то проверяем введенные данные с данными, которые у нас есть.
    # Если были введены верные данные, то переводим его на основную
    # страницу.
    # Иначе просим его ввести данные снова.

    user = User("admin", "admin")

    # Проверяем, если пользователь уже зашел,
    # то отправляем его на основную страницу.
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    # Создаем объект form, который содержит в себе веб-формы для
    # авторизации
    form = LoginForm()
    # Если пришел POST запрос от браузера
    if form.validate_on_submit():
        if user.username != form.username.data or user.check_password(form.password.data) is False:
            flash('Invalid username or password')
            return redirect(url_for('login'))
        # Иначе загружаем пользователя
        # и переходим к основной странице
        login_user(user, remember=form.remember.data)
        # Проверяем, если в строке был указан аргумент next,
        # значит пользователь пытался перейти на страницу для
        # авторизованных пользователей, но так как он не авторизовалься,
        # его перенаправили сюда. Тогда после того, как он
        # авторизовался, переходим на стрницу указанную страницу.
        next_page = request.args.get("next")
        # Если аргумента next нет, то переходим на главную страницу
        if next_page is None or url_parse(next_page).netloc != '':
            next_page = url_for("index")
        return redirect(next_page)
    # Генерируем страницу авторизиции
    return render_template("login.html", title="Login", form=form)



@flsk.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))