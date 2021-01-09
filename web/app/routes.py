# Данные файл содержит в себе функции для отображения страниц, по
# указанным путям


from app import flsk
from flask import render_template, flash, redirect, url_for, request
from app.forms import LoginForm, NavigationForm, TableRowForm, TableNewRowForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from werkzeug.urls import url_parse
import sqlite3


# TODO: Убрать обновление страницы, если в этом нет нужды

first = True


@flsk.route("/index", methods=["GET", "POST"])
@login_required # Проверяем авторизовался ли пользователь
def index():
    db = sqlite3.connect("../data/database.db")
    fuel_data = db.execute("SELECT id, name FROM fuel ORDER BY id")
    navig_data = db.execute("SELECT CAST(id as TEXT), name FROM fuel")

    navig_form = NavigationForm()
    navig_form.names.choices = list(navig_data)

    row_form = TableRowForm()

    new_row_form = TableNewRowForm()

    try:
        db.execute("DROP VIEW IF EXISTS vtrans")
        db.execute("""CREATE VIEW vtrans AS SELECT
                    t.id, t.fuel_id, t.dtime, t.odometer, f.name, t.amount
                    FROM trans t, fuel f WHERE t.fuel_id = f.id
                    ORDER BY t.dtime""")
    except sqlite3.Error as e:
        flsk.logger.error(e)

    if row_form.validate_on_submit() or navig_form.validate_on_submit() or new_row_form.validate_on_submit():
        flsk.logger.debug("Index page submitted")
        if row_form.save.data:
            flsk.logger.info("Row form save button was pressed")
            try:
                db.execute("UPDATE trans" +
                           " SET dtime = '" + str(row_form.date.data) + "'" +
                           ", odometer = " + str(row_form.odometer.data) +
                           ", fuel_id = " + str(row_form.fuel_station.data) +
                           ", amount = " + str(row_form.gallon_count.data) + 
                           " WHERE id = " + str(row_form.id.data))
                db.commit()
            except sqlite3.Error as e:
                flsk.logger.error(e)
        elif navig_form.allow.data:
            flsk.logger.debug("Navigation form allow button was pressed")
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
            try:
                db.execute("DROP VIEW IF EXISTS vtrans")
                db.execute(command)
            except sqlite3.Error as e:
                flsk.logger.error(e)
        elif row_form.delete.data:
            flsk.logger.debug("Row form delete button was pressed")
            try:
                db.execute("DELETE FROM trans WHERE id = " + str(row_form.id.data))
                db.commit()
            except sqlite3.Error as e:
                flsk.logger.error(e)
        elif new_row_form.add.data:
            flsk.logger.debug("New row form add button was pressed")
            try:
                db.execute("INSERT INTO trans(dtime, odometer, fuel_id, amount) VALUES (" +
                           "'" + str(new_row_form.date.data) + "'" +
                           ", " + str(new_row_form.odometer.data) + 
                           ", " + str(new_row_form.fuel_station.data) +
                           ", " + str(new_row_form.gallon_count.data) + ")")
            except sqlite3.Error as e:
                flsk.logger.error(e)
            db.commit()
        else:
            return
    try:
        trans_data = db.execute("""SELECT id, fuel_id, dtime, odometer, name, amount
                                FROM vtrans""")
    except sqlite3.Error as e:
        flsk.logger.error(e)

    flsk.logger.debug("Rendering index page")
    return render_template("index.html",
                           trans_data=trans_data,
                           fuel_data=fuel_data,
                           navig_form=navig_form,
                           row_form=row_form,
                           new_row_form=new_row_form)



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
        flsk.logger.info("User already autheticated")
        return redirect(url_for('index'))
    # Создаем объект form, который содержит в себе веб-формы для
    # авторизации
    form = LoginForm()
    # Если пришел POST запрос от браузера
    if form.validate_on_submit():
        flsk.logger.debug("Ligun page submitted")
        if user.username != form.username.data or user.check_password(form.password.data) is False:
            flsk.logger.info("'Invalid username or password'")
            flash('Invalid username or password')
            return redirect(url_for('login'))
        # Иначе загружаем пользователя
        # и переходим к основной странице
        login_user(user, remember=form.remember.data)
        flsk.logger.info("User signed in")
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
    flsk.logger.debug("Rendering login page")
    return render_template("login.html", title="Login", form=form)



@flsk.route('/logout')
@login_required
def logout():
    flsk.logger.info("User logouted")
    logout_user()
    return redirect(url_for('index'))