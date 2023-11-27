from faker import Faker
import random
from datetime import datetime

fake = Faker()

def generate_users(n):
    users = []
    for _ in range(n):
        first_name = fake.first_name()
        last_name = fake.last_name()
        email = fake.email()
        password = fake.password()
        date_joined = fake.date_between(start_date='-5y', end_date='today').strftime('%Y-%m-%d')
        total_savings = round(random.uniform(1000, 10000), 2)
        total_expenses = round(random.uniform(500, 9000), 2)
        bank_balance = total_savings - total_expenses
        users.append((first_name, last_name, email, password, date_joined, total_savings, total_expenses, bank_balance))
    return users

def generate_groups(n):
    groups = []
    for _ in range(n):
        group_name = fake.company()
        description = fake.catch_phrase()
        group_goal = round(random.uniform(5000, 20000), 2)
        current_group_savings = round(random.uniform(1000, group_goal), 2)
        groups.append((group_name, description, group_goal, current_group_savings))
    return groups

def generate_expenses(n, user_count):
    expenses = []
    for _ in range(n):
        user_id = random.randint(1, user_count)
        amount = round(random.uniform(10, 500), 2)
        category = fake.word()
        date = fake.date_between(start_date='-2y', end_date='today').strftime('%Y-%m-%d')
        expenses.append((user_id, amount, category, date))
    return expenses

def generate_savings(n, user_count):
    savings = []
    for _ in range(n):
        user_id = random.randint(1, user_count)
        amount = round(random.uniform(100, 2000), 2)
        purpose = fake.sentence(nb_words=4)
        date = fake.date_between(start_date='-2y', end_date='today').strftime('%Y-%m-%d')
        savings.append((user_id, amount, purpose, date))
    return savings

def generate_challenges(n):
    challenges = []
    for _ in range(n):
        name = fake.sentence(nb_words=3)
        brief_description = fake.sentence(nb_words=6)
        description = fake.text()
        start_date_str = fake.date_between(start_date='-2y', end_date='today').strftime('%Y-%m-%d')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()  # Convert to date object
        end_date = fake.date_between(start_date=start_date, end_date='+1y').strftime('%Y-%m-%d')
        target_amount = round(random.uniform(500, 5000), 2)
        challenges.append((name, brief_description, description, start_date_str, end_date, target_amount))
    return challenges

def generate_user_groups(n, user_count, group_count):
    user_groups = []
    for _ in range(n):
        user_id = random.randint(1, user_count)
        group_id = random.randint(1, group_count)
        user_groups.append((user_id, group_id))
    return user_groups

def generate_user_challenges(n, user_count, challenge_count):
    user_challenges = []
    for _ in range(n):
        user_id = random.randint(1, user_count)
        challenge_id = random.randint(1, challenge_count)
        user_challenges.append((user_id, challenge_id))
    return user_challenges

def save_to_file(filename, data, table_name, columns):
    with open(filename, 'a') as file:
        for record in data:
            values = ', '.join([f"'{str(v)}'" for v in record])  # Treat all values as strings
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({values});\n"
            file.write(query)

def main():
    n_users = int(input("Enter the number of Users to generate: "))
    n_groups = int(input("Enter the number of Groups to generate: "))
    n_expenses = int(input("Enter the number of Expenses to generate: "))
    n_savings = int(input("Enter the number of Savings to generate: "))
    n_challenges = int(input("Enter the number of Challenges to generate: "))
    n_user_groups = int(input("Enter the number of User-Group relations to generate: "))
    n_user_challenges = int(input("Enter the number of User-Challenge relations to generate: "))

    users = generate_users(n_users)
    groups = generate_groups(n_groups)
    expenses = generate_expenses(n_expenses, n_users)
    savings = generate_savings(n_savings, n_users)
    challenges = generate_challenges(n_challenges)
    user_groups = generate_user_groups(n_user_groups, n_users, n_groups)
    user_challenges = generate_user_challenges(n_user_challenges, n_users, n_challenges)

    save_to_file('mock_data.sql', users, 'Users', ['FirstName', 'LastName', 'Email', 'Password', 'DateJoined', 'TotalSavings', 'TotalExpenses', 'BankBalance'])
    save_to_file('mock_data.sql', groups, 'Groups', ['GroupName', 'Description', 'GroupGoal', 'CurrentGroupSavings'])
    save_to_file('mock_data.sql', expenses, 'Expenses', ['UserID', 'Amount', 'Category', 'Date'])
    save_to_file('mock_data.sql', savings, 'Savings', ['UserID', 'Amount', 'Purpose', 'Date'])
    save_to_file('mock_data.sql', challenges, 'Challenges', ['Name', 'BriefDescription', 'Description', 'StartDate', 'EndDate', 'TargetAmount'])
    save_to_file('mock_data.sql', user_groups, 'UserGroups', ['UserID', 'GroupID'])
    save_to_file('mock_data.sql', user_challenges, 'UserChallenges', ['UserID', 'ChallengeID'])

if __name__ == "__main__":
    main()
