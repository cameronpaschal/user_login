import getpass
import sys
from typing import Callable, Dict

from user_service import (
    DatabaseConfig,
    UserServiceError,
    get_database_config_from_env,
    create_user,
    delete_user,
    get_user,
    list_users,
    login,
    update_user,
)


def _print_menu() -> None:
    print(
        "\nChoose an option:\n"
        "1) Create user\n"
        "2) View a user's info\n"
        "3) Update a user\n"
        "4) Delete a user\n"
        "5) List all users\n"
        "6) Test login\n"
        "7) Quit"
    )


def _create(config: DatabaseConfig) -> None:
    username = input("Username: ").strip()
    display_name = input("Display name: ").strip()
    email = input("Email: ").strip()
    religion = input("Religion: ").strip()
    password = getpass.getpass("Password: ")
    user_id = create_user(config, username, display_name, email, religion, password)
    print(f"Created user '{username}' with id {user_id}.")


def _view(config: DatabaseConfig) -> None:
    username = input("Enter a Username: ").strip()
    user = get_user(config, username=username)
    print(
        "ID: {id}\nUsername: {username}\nDisplay name: {display_name}\nEmail: {email}\nReligion: {religion}\nCreated: {created_at}\nUpdated: {updated_at}".format(
            **user
        )
    )


def _update(config: DatabaseConfig) -> None:
    username = input("Username to update: ").strip()
    new_username = input("New username (leave blank to keep current): ").strip() or None
    new_display_name = (
        input("New display name (leave blank to keep current): ").strip() or None
    )
    new_email = input("New email (leave blank to keep current): ").strip() or None
    new_religion = input("New religion (leave blank to keep current): ").strip() or None
    change_pwd = input("Change password? (y/N): ").strip().lower() == "y"
    new_password = getpass.getpass("New password: ") if change_pwd else None
    update_user(
        config,
        username=username,
        new_username=new_username,
        new_display_name=new_display_name,
        new_email=new_email,
        new_religion=new_religion,
        new_password=new_password,
    )
    print(f"Updated '{username}'.")


def _delete(config: DatabaseConfig) -> None:
    username = input("Username to delete: ").strip()
    confirm = input(f"Type the username ({username}) to confirm: ").strip()
    if confirm != username:
        print("Confirmation did not match. Please try again.")
        return
    delete_user(config, username)
    print(f"Deleted '{username}'.")


def _list(config: DatabaseConfig) -> None:
    users = list_users(config)
    if not users:
        print("No users found.")
        return
    for user in users:
        print(f"[{user['id']}] {user['username']} ({user['display_name']}) - {user['email']} - {user['religion']}")


def _test_login(config: DatabaseConfig) -> None:
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    profile = login(config, username, password)
    print(f"You're in! Authenticated as {profile['display_name']} ({profile['email']}).")


ACTIONS: Dict[str, Callable[[DatabaseConfig], None]] = {
    "1": _create,
    "2": _view,
    "3": _update,
    "4": _delete,
    "5": _list,
    "6": _test_login,
}


def main() -> int:
    config = get_database_config_from_env()
    while True:
        _print_menu()
        choice = input("Enter choice: ").strip()
        if choice == "7":
            print("Goodbye!")
            return 0
        action = ACTIONS.get(choice)
        if not action:
            print("Invalid choice.")
            continue
        try:
            action(config)
        except UserServiceError as exc:
            print(f"Error: {exc}")
        except ValueError as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    sys.exit(main())
