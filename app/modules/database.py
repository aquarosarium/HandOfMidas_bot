import logging
import time
from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, Numeric, String, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/hom_db"


# Функция для ожидания подключения к БД
def wait_for_db():
    max_retries = 30
    retry_interval = 2

    for attempt in range(max_retries):
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                logger.info("✅ Successfully connected to database")
                return engine
        except OperationalError as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"⚠️ Database not ready, retrying in {retry_interval}s... (Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(retry_interval)
            else:
                logger.error("❌ Could not connect to database after all retries")
                raise e


# Настройка базы данных
engine = wait_for_db()
Base = declarative_base()


# Таблица для операций (расходы и доходы)
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    date = Column(Date, nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    type = Column(String, nullable=False)  # 'income' или 'expense'


# Таблица для балансов пользователей (рубли)
class UserBalance(Base):
    __tablename__ = "user_balances"
    chat_id = Column(BigInteger, primary_key=True)
    balance = Column(Numeric(10, 2), default=0)
    last_updated = Column(Date)


# Таблица для валютных балансов
class UserCurrency(Base):
    __tablename__ = "user_currencies"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    currency = Column(String, nullable=False)  #'USD', 'CNY'
    amount = Column(Numeric(10, 2), default=0)
    last_updated = Column(Date)


# Создание таблиц с обработкой ошибок
def init_db():
    try:
        Base.metadata.create_all(engine)
        logger.info("✅ Database tables created successfully")
    except OperationalError as e:
        logger.error(f"❌ Error creating database tables: {e}")
        raise


init_db()

Session = sessionmaker(bind=engine)

# Добавление транзакции в бд
def add_transaction(chat_id, date, category, amount, is_income):
    try:
        session = Session() # Начинаем сессию
        transaction_type = "income" if is_income else "expense" # Определяем тип операции

        transaction = Transaction( # Определяем транзакцию
            chat_id=chat_id,
            date=date,
            category=category,
            amount=amount,
            type=transaction_type,
        )
        session.add(transaction)

        today = datetime.now().date()
        
        balance_record = session.query(UserBalance).filter(UserBalance.chat_id == chat_id).first() # Ищем существующий баланс
        
        balance_change = amount if is_income else -amount         # Рассчитываем изменение баланса ДОХОД: +amount, РАСХОД: -amount
        
        if balance_record:  #Если существует запись баланса
            balance_record.balance += balance_change # Обновляем существующий баланс
        else:   #Иначе
            balance_record = UserBalance(             # Создаем новый баланс
                chat_id=chat_id,    # Передаём chat id
                balance=balance_change,     # Передаём изменение баланса
            )
            session.add(balance_record) # Добавляем

        session.commit()
        session.close()
        logger.info(
            f"✅ Transaction added for chat_id {chat_id}: {category} - {amount} ({transaction_type})"
        )
    except OperationalError as e:
        logger.error(f"❌ Error adding transaction: {e}")
        raise

# Получение транзакций из бд (надо удалить из /dev ветки)
def get_transactions(chat_id):
    """Получает все операции пользователя"""
    try:
        session = Session()
        transactions = (
            session.query(Transaction)
            .filter(
                Transaction.chat_id == chat_id
                )
                .all()
        )
        session.close()
        return transactions
    except OperationalError as e:
        logger.error(f"❌ Error getting transactions: {e}")
        raise

# Получение транзакций по периоду
def get_transactions_by_period(chat_id, start_date, end_date):
    """Получить операции за определенный период"""
    try:
        session = Session()
        transactions = (
            session.query(Transaction)
            .filter(
                Transaction.chat_id == chat_id,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
            )
            .all()
        )
        session.close()
        return transactions
    except OperationalError as e:
        logger.error(f"❌ Error getting transactions by period: {e}")
        raise

# Получение баланса юзера 
def get_user_balance(chat_id):
    """Получить баланс пользователя (рубли)"""
    try:
        session = Session()
        balance_record = (
            session.query(UserBalance).filter(UserBalance.chat_id == chat_id).first()
        )
        session.close()

        if balance_record:
            return balance_record.balance
        else:
            return 0
    except OperationalError as e:
        logger.error(f"❌ Error getting user balance: {e}")
        raise

# Сброс баланса юзера
def reset_user_balance(chat_id, new_balance=0):
    """Сбросить баланс пользователя"""
    try:
        session = Session()
        today = datetime.now().date()

        balance_record = (
            session.query(UserBalance).filter(UserBalance.chat_id == chat_id).first()
        )

        if balance_record:
            balance_record.balance = new_balance
            balance_record.last_updated = today
        else:
            balance_record = UserBalance(
                chat_id=chat_id, balance=new_balance, last_updated=today
            )
            session.add(balance_record)

        session.commit()
        session.close()

        logger.info(f"✅ User {chat_id} balance reset to: {new_balance}")
        return new_balance

    except OperationalError as e:
        logger.error(f"❌ Error resetting user balance: {e}")
        raise

# Сброс всех данных о юзере из бд
def delete_all_user_data(chat_id):
    """Удалить все данные пользователя (операции и балансы)"""
    try:
        session = Session()

        # Удаляем все операции пользователя
        transactions_deleted = (
            session.query(Transaction).filter(Transaction.chat_id == chat_id).delete()
        )

        # Удаляем рублевый баланс пользователя
        balance_deleted = (
            session.query(UserBalance).filter(UserBalance.chat_id == chat_id).delete()
        )

        # Удаляем валютные балансы пользователя
        currencies_deleted = (
            session.query(UserCurrency).filter(UserCurrency.chat_id == chat_id).delete()
        )

        session.commit()
        session.close()

        logger.info(
            f"✅ User {chat_id} data deleted: {transactions_deleted} transactions, {balance_deleted} balance records, {currencies_deleted} currency records"
        )
        return transactions_deleted, balance_deleted, currencies_deleted

    except OperationalError as e:
        logger.error(f"❌ Error deleting user data: {e}")
        raise


''' Функции для работы с валютами '''

# Получение списка валют юзера
def get_user_currencies(chat_id):
    """Получить все валютные балансы пользователя"""
    try:
        session = Session()
        currencies = (
            session.query(UserCurrency)
            .filter(UserCurrency.chat_id == chat_id)
            .all()
        )
        session.close()
        return currencies
    except OperationalError as e:
        logger.error(f"❌ Error getting user currencies: {e}")
        raise

# Получение доллара юзера
def get_user_usd(chat_id):
    """Получить все валютные балансы пользователя"""
    try:
        session = Session()
        currencies = (
            session.query(UserCurrency)
            .filter(UserCurrency.chat_id == chat_id)
            .filter(UserCurrency.currency == 'USD')
            .all()
        )
        session.close()
        return currencies
    except OperationalError as e:
        logger.error(f"❌ Error getting user currencies: {e}")
        raise

# Получение йен юзера
def get_user_cny(chat_id):
    """Получить все валютные балансы пользователя"""
    try:
        session = Session()
        currencies = (
            session.query(UserCurrency)
            .filter(UserCurrency.chat_id == chat_id)
            .filter(UserCurrency.currency == 'CNY')
            .all()
        )
        session.close()
        return currencies
    except OperationalError as e:
        logger.error(f"❌ Error getting user currencies: {e}")
        raise

# Обновление валюты
def update_user_currency(chat_id, currency, amount):
    """Обновить или создать валютный баланс пользователя"""
    try:
        session = Session()
        today = datetime.now().date()

        # Конвертируем amount в Decimal если это float
        from decimal import Decimal

        if isinstance(amount, float):
            amount = Decimal(str(amount))

        # Ищем существующую запись
        currency_record = (
            session.query(UserCurrency)
            .filter(UserCurrency.chat_id == chat_id, UserCurrency.currency == currency)
            .first()
        )

        if currency_record:
            # Обновляем существующую запись
            currency_record.amount = amount
            currency_record.last_updated = today
        else:
            # Создаем новую запись
            currency_record = UserCurrency(
                chat_id=chat_id, currency=currency, amount=amount, last_updated=today
            )
            session.add(currency_record)

        session.commit()
        session.close()

        logger.info(f"✅ User {chat_id} {currency} balance updated: {amount}")
        return amount

    except OperationalError as e:
        logger.error(f"❌ Error updating user currency: {e}")
        raise

# Удаление валюты
def delete_user_currency(chat_id, currency):
    try:
        session = Session()

        deleted = (
            session.query(UserCurrency)
            .filter(UserCurrency.chat_id == chat_id, UserCurrency.currency == currency)
            .delete()
        )

        session.commit()
        session.close()

        logger.info(f"✅ User {chat_id} {currency} balance deleted")
        return deleted

    except OperationalError as e:
        logger.error(f"❌ Error deleting user currency: {e}")
        raise

# Создание валютного баланса
def create_currency_balance(chat_id, currency):
    """Создает валютный баланс пользователя с нулевым значением"""
    try:
        session = Session()
        today = datetime.now().date()

        # Проверяем, существует ли уже запись
        existing_record = (
            session.query(UserCurrency)
            .filter(UserCurrency.chat_id == chat_id, UserCurrency.currency == currency)
            .first()
        )

        if existing_record:
            # Баланс уже существует, возвращаем текущее значение
            session.close()
            return existing_record.amount
        else:
            # Создаем новую запись с нулевым балансом
            currency_record = UserCurrency(
                chat_id=chat_id, currency=currency, amount=0, last_updated=today
            )
            session.add(currency_record)
            session.commit()
            session.close()

            logger.info(f"✅ User {chat_id} {currency} balance created with 0")
            return 0

    except OperationalError as e:
        logger.error(f"❌ Error creating currency balance: {e}")
        raise