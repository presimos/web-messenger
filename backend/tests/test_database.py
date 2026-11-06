from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Chat, ChatMember, Message, User


def test_database_tables_are_created(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(bind=engine)

    assert set(inspect(engine).get_table_names()) == {
        "users",
        "chats",
        "chat_members",
        "messages",
    }


def test_message_can_be_saved_with_chat_and_user(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    user = User(username="demo", password_hash="hash")
    chat = Chat(title="Тестовый чат")
    session.add_all([user, chat])
    session.flush()
    message = Message(chat_id=chat.id, sender_id=user.id, body="Проверка")
    session.add(message)
    session.commit()

    assert session.get(Message, message.id).body == "Проверка"
    session.close()
