import tkinter as tk
from tkinter import messagebox, Toplevel, Menu, ttk, PhotoImage
import tkinter.simpledialog as simpledialog
from typing import Self
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import psycopg2

def open_login_window():
    global login_window  # Ensure that we can re-open the window
    login_window = LoginWindow(db)
    login_window.run()

class Database:
    def __init__(self, dbname, user, password, host):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host

    def connect(self):
        return psycopg2.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host
        )

    def get_user_info(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM Users WHERE UserID = %s", (user_id,))
                return cur.fetchone()

    def login_user(self, email, password):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT UserID, Password FROM Users WHERE Email = %s", (email,))
                user_record = cur.fetchone()
                if user_record and user_record[1] == password:
                    return user_record[0]  # Return the UserID
                else:
                    return None

    def get_group_goals(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT g.GroupID, g.GroupName, g.GroupGoal, g.CurrentGroupSavings
                    FROM Groups g
                    INNER JOIN UserGroups ug ON g.GroupID = ug.GroupID
                    WHERE ug.UserID = %s;
                """, (user_id,))
                return cur.fetchall()

    def get_groups_user_not_member_of(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT g.GroupID, g.GroupName, g.Description, g.GroupGoal, COUNT(ug.UserID)
                    FROM Groups g
                    LEFT JOIN UserGroups ug ON g.GroupID = ug.GroupID
                    WHERE g.GroupID NOT IN (
                        SELECT GroupID FROM UserGroups WHERE UserID = %s
                    )
                    GROUP BY g.GroupID
                    ORDER BY g.GroupName;
                """, (user_id,))
                return cur.fetchall()

    def create_group(self, user_id, group_name, description, group_goal):
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    # Insert the new group
                    cur.execute("""
                        INSERT INTO Groups (GroupName, Description, GroupGoal, CurrentGroupSavings, OwnerID) 
                        VALUES (%s, %s, %s, 0.00, %s) RETURNING GroupID;
                    """, (group_name, description, group_goal, user_id))
                    group_id = cur.fetchone()[0]

                    # Associate the creator with the group in UserGroups table
                    cur.execute("""
                        INSERT INTO UserGroups (UserID, GroupID) VALUES (%s, %s);
                    """, (user_id, group_id))

                    conn.commit()
                    return group_id
                except Exception as e:
                    conn.rollback()
                    raise e

    def edit_group(self, user_id, group_id, new_group_name, new_description, new_group_goal):
        with self.connect() as conn:
            with conn.cursor() as cur:
                # Check if the user is the owner of the group
                cur.execute("SELECT OwnerID FROM Groups WHERE GroupID = %s", (group_id,))
                result = cur.fetchone()
                if result and result[0] == user_id:
                    cur.execute("""
                        UPDATE Groups SET GroupName = %s, Description = %s, GroupGoal = %s 
                        WHERE GroupID = %s;
                    """, (new_group_name, new_description, new_group_goal, group_id))
                    conn.commit()
                else:
                    raise Exception("User is not the owner of the group.")

    def delete_group(self, user_id, group_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT OwnerID FROM Groups WHERE GroupID = %s", (group_id,))
                result = cur.fetchone()
                if result and result[0] == user_id:
                    cur.execute("DELETE FROM Groups WHERE GroupID = %s", (group_id,))
                    conn.commit()
                else:
                    raise Exception("User is not the owner of the group.")

    def add_user_to_group(self, user_id, group_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO UserGroups (UserID, GroupID) VALUES (%s, %s);
                """, (user_id, group_id))
                conn.commit()

    def add_contribution_to_group(self, group_id, amount):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE Groups SET CurrentGroupSavings = CurrentGroupSavings + %s WHERE GroupID = %s;
                """, (amount, group_id))
                conn.commit()

    def get_group_name(self, group_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT GroupName FROM Groups WHERE GroupID = %s", (group_id,))
                result = cur.fetchone()
                return result[0] if result else None

    def get_savings_leaderboard_data(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                # SQL query to fetch user details and their total savings
                query = """
                SELECT u.UserID, u.FirstName, u.LastName, COALESCE(SUM(s.Amount), 0) AS TotalSavings
                FROM Users u
                LEFT JOIN Savings s ON u.UserID = s.UserID
                GROUP BY u.UserID
                ORDER BY TotalSavings DESC;
                """
                cur.execute(query)
                return cur.fetchall()
            
    def get_expense_leaderboard_data(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                # SQL query to fetch user details and their total savings
                query = """
                SELECT u.UserID, u.FirstName, u.LastName, COALESCE(SUM(e.Amount), 0) AS TotalExpense
                FROM Users u
                LEFT JOIN Expenses e ON u.UserID = e.UserID
                GROUP BY u.UserID
                ORDER BY TotalExpense DESC
                """
                cur.execute(query)
                return cur.fetchall()
            
    def get_net_worth_leaderboard_data(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                query = """
                WITH TotalSavings AS (
                    SELECT UserID, COALESCE(SUM(Amount), 0) AS SavingsTotal
                    FROM Savings
                    GROUP BY UserID
                ),
                TotalExpenses AS (
                    SELECT UserID, COALESCE(SUM(Amount), 0) AS ExpensesTotal
                    FROM Expenses
                    GROUP BY UserID
                )
                SELECT u.UserID, u.FirstName, u.LastName, 
                       COALESCE(ts.SavingsTotal, 0) - COALESCE(te.ExpensesTotal, 0) AS NetWorth
                FROM Users u
                LEFT JOIN TotalSavings ts ON u.UserID = ts.UserID
                LEFT JOIN TotalExpenses te ON u.UserID = te.UserID
                ORDER BY NetWorth DESC;
                """
                cur.execute(query)
                return cur.fetchall()
            
    def get_total_number_of_users(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM Users;")
                result = cur.fetchone()
                return result[0] if result else 0
        
    def create_user(self, first_name, last_name, email, password):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO Users (FirstName, LastName, Email, Password, DateJoined) "
                    "VALUES (%s, %s, %s, %s, CURRENT_DATE) RETURNING UserID;",
                    (first_name.capitalize(), last_name.capitalize(), email, password)
                )
                user_id = cur.fetchone()[0]
                conn.commit()
                return user_id
            
    def add_new_saving(self, user_id, amount, purpose):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO Savings (UserID, Amount, Purpose, Date) VALUES (%s, %s, %s, CURRENT_DATE) RETURNING SavingsID;",
                    (user_id, amount, purpose)
                )
                savings_id = cur.fetchone()[0]
                conn.commit()
                return savings_id

    def delete_saving(self, user_id, savings_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM Savings WHERE UserID = %s AND SavingsID = %s;",
                    (user_id, savings_id)
                )
                conn.commit()
                return cur.rowcount > 0  # Returns True if a row was deleted

    def edit_saving(self, user_id, savings_id, new_amount, new_purpose):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE Savings SET Amount = %s, Purpose = %s WHERE UserID = %s AND SavingsID = %s;",
                    (new_amount, new_purpose, user_id, savings_id)
                )
                conn.commit()
                return cur.rowcount > 0  # Returns True if a row was updated
    def add_new_expense(self, user_id, amount, category):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO Expenses (UserID, Amount, Category, Date) VALUES (%s, %s, %s, CURRENT_DATE)",
                    (user_id, amount, category)
                )
                conn.commit()

    def delete_expense(self, user_id, expense_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM Expenses WHERE UserID = %s AND ExpenseID = %s",
                    (user_id, expense_id)
                )
                conn.commit()

    def edit_expense(self, user_id, expense_id, new_amount, new_category, new_date):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE Expenses SET Amount = %s, Category = %s, Date = %s WHERE UserID = %s AND ExpenseID = %s",
                    (new_amount, new_category, new_date, user_id, expense_id)
                )
                conn.commit()
            
    def get_user_savings(self, user_id, sort_by='date', order='asc'):
        with self.connect() as conn:
            with conn.cursor() as cur:
                order_by = 'DESC' if order == 'desc' else 'ASC'
                if sort_by == 'amount':
                    query = "SELECT * FROM Savings WHERE UserID = %s ORDER BY Amount " + order_by
                elif sort_by == 'date':
                    query = "SELECT * FROM Savings WHERE UserID = %s ORDER BY Date " + order_by
                # Add more sorting options as needed

                cur.execute(query, (user_id,))
                return cur.fetchall()
    def get_user_expenses(self, user_id, sort_by='date', order='asc'):
        with self.connect() as conn:
            with conn.cursor() as cur:
                order_by = 'DESC' if order == 'desc' else 'ASC'
                if sort_by == 'amount':
                    query = "SELECT * FROM Expenses WHERE UserID = %s ORDER BY Amount " + order_by
                elif sort_by == 'date':
                    query = "SELECT * FROM Expenses WHERE UserID = %s ORDER BY Date " + order_by
                # Add more sorting options as needed

                cur.execute(query, (user_id,))
                return cur.fetchall()
    
    def get_total_savings(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT SUM(Amount) FROM Savings WHERE UserID = %s", (user_id,))
                return cur.fetchone()[0] or 0

    def get_total_expenses(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT SUM(Amount) FROM Expenses WHERE UserID = %s", (user_id,))
                return cur.fetchone()[0] or 0
    def get_highest_and_lowest_savings(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(Amount), MIN(Amount) FROM Savings WHERE UserID = %s", (user_id,))
                return cur.fetchone()  # Returns (highest amount, lowest amount)

    def get_highest_and_lowest_expenses(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(Amount), MIN(Amount) FROM Expenses WHERE UserID = %s", (user_id,))
                return cur.fetchone()  # Returns (highest amount, lowest amount)

    def get_number_of_savings_entries(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM Savings WHERE UserID = %s", (user_id,))
                return cur.fetchone()[0]  # Returns the number of savings entries

    def get_number_of_expenses_entries(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM Expenses WHERE UserID = %s", (user_id,))
                return cur.fetchone()[0]  # Returns the number of expenses entries

    def get_savings_expenses_over_time(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                query = """
                SELECT s.Date, COALESCE(SUM(s.Amount), 0) AS TotalSavings, COALESCE(SUM(e.Amount), 0) AS TotalExpenses
                FROM Savings s
                FULL OUTER JOIN Expenses e ON s.Date = e.Date AND s.UserID = e.UserID
                WHERE s.UserID = %s OR e.UserID = %s
                GROUP BY s.Date
                ORDER BY s.Date
                """
                cur.execute(query, (user_id, user_id))
                return cur.fetchall()
    def get_user_challenges(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.ChallengeID, c.Name, c.Description, c.StartDate, c.EndDate, c.TargetAmount, c.currentAmount
                    FROM Challenges c
                    INNER JOIN UserChallenges uc ON c.ChallengeID = uc.ChallengeID
                    WHERE uc.UserID = %s;
                """, (user_id,))
                challenges = cur.fetchall()
                print("Challenges fetched:", challenges)  # Debug print
            return challenges
    def add_new_challenge(self, name, description, end_date, target_amount, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                # Insert the new challenge into the Challenges table
                cur.execute("""
                    INSERT INTO Challenges (Name, Description, StartDate, EndDate, TargetAmount)
                    VALUES (%s, %s, CURRENT_DATE, %s, %s) RETURNING ChallengeID;
                """, (name, description, end_date, target_amount))
                challenge_id = cur.fetchone()[0]

                # Link the challenge with the user in the UserChallenges table
                cur.execute("""
                    INSERT INTO UserChallenges (UserID, ChallengeID)
                    VALUES (%s, %s);
                """, (user_id, challenge_id))

                conn.commit()
                return challenge_id
    
            
    def delete_challenge(self, challenge_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                # Delete the challenge from the Challenges table
                cur.execute("DELETE FROM Challenges WHERE ChallengeID = %s;", (challenge_id,))
                conn.commit()


    def get_user_net_savings(self, user_id):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT TotalSavings, TotalExpenses FROM Users WHERE UserID = %s;", (user_id,))
                result = cur.fetchone()
                if result:
                    total_savings, total_expenses = result
                    return total_savings - total_expenses
                else:
                    return 0  # Or handle the user not found case appropriately


    def move_money_to_challenge(self, user_id, challenge_id, amount):
        with self.connect() as conn:
            with conn.cursor() as cur:
                # First, check if the user has enough net savings
                net_savings = self.get_user_net_savings(user_id)
                if net_savings >= amount:
                    # Update the challenge's currentAmount
                    cur.execute("""
                        UPDATE Challenges SET currentAmount = currentAmount + %s WHERE ChallengeID = %s;
                    """, (amount, challenge_id))

                    # Record the transaction as an expense
                    cur.execute("""
                        INSERT INTO Expenses (UserID, Amount, Category, Date) VALUES (%s, %s, 'Challenge Contribution', CURRENT_DATE);
                    """, (user_id, amount))

                    # Update the user's TotalExpenses
                    cur.execute("""
                        UPDATE Users SET TotalExpenses = TotalExpenses + %s WHERE UserID = %s;
                    """, (amount, user_id))

                    conn.commit()
                    return True
                else:
                    return False  # Not enough savings
class LoginWindow:
    def __init__(self, database):
        self.database = database
        self.root = tk.Tk()
        self.root.title("Welcome to SaveSphere")
        self.root.geometry("600x600")

        self.create_widgets()

    def create_widgets(self):
        header_label = tk.Label(self.root, text="Welcome to SaveSphere", font=("Arial", 20))
        header_label.pack(pady=(20, 10))

        email_login_label = tk.Label(self.root, text="Email", font=("Arial", 14))
        email_login_label.pack()
        self.email_login_entry = tk.Entry(self.root, font=("Arial", 14))
        self.email_login_entry.pack(pady=(0, 10))

        password_login_label = tk.Label(self.root, text="Password", font=("Arial", 14))
        password_login_label.pack()
        self.password_login_entry = tk.Entry(self.root, font=("Arial", 14), show="*")
        self.password_login_entry.pack(pady=(0, 20))

        login_button = tk.Button(self.root, text="Login", font=("Arial", 14), bg="#FFA07A", command=self.on_login_click)
        login_button.pack(pady=(0, 20))

        create_user_button = tk.Button(self.root, text="No login? Create user", font=("Arial", 14), bg="#FFA07A", command=self.on_create_user_click)
        create_user_button.pack(side=tk.RIGHT, padx=(20, 50), pady=(0, 20))

    def on_login_click(self):
        user_email = self.email_login_entry.get()
        user_password = self.password_login_entry.get()
        user_id = self.database.login_user(user_email, user_password)
        if user_id:
            self.root.destroy()  # Close the login window
            DashboardWindow(self.database, user_id)  # Open the dashboard window
        else:
            messagebox.showerror("Login Failed", "Invalid email or password.")

    def on_create_user_click(self):
        CreateUserWindow(self.database)

    def run(self):
        self.root.mainloop()

class CreateUserWindow:
    def __init__(self, database):
        self.database = database
        self.create_user_window = Toplevel()
        self.create_user_window.title("Create New User")
        self.create_user_window.geometry("400x300")

        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.create_user_window, text="First Name:").grid(row=0, column=0, sticky='w')
        self.first_name_entry = tk.Entry(self.create_user_window)
        self.first_name_entry.grid(row=0, column=1)

        tk.Label(self.create_user_window, text="Last Name:").grid(row=1, column=0, sticky='w')
        self.last_name_entry = tk.Entry(self.create_user_window)
        self.last_name_entry.grid(row=1, column=1)

        tk.Label(self.create_user_window, text="Email:").grid(row=2, column=0, sticky='w')
        self.email_entry = tk.Entry(self.create_user_window)
        self.email_entry.grid(row=2, column=1)

        tk.Label(self.create_user_window, text="Password:").grid(row=3, column=0, sticky='w')
        self.password_entry = tk.Entry(self.create_user_window, show="*")
        self.password_entry.grid(row=3, column=1)

        submit_button = tk.Button(self.create_user_window, text="Submit", command=self.create_user)
        submit_button.grid(row=4, column=1, pady=10)

    def create_user(self):
        first_name = self.first_name_entry.get()
        last_name = self.last_name_entry.get()
        email = self.email_entry.get()
        password = self.password_entry.get()
        user_id = self.database.create_user(first_name, last_name, email, password)
        if user_id:
            messagebox.showinfo("Success", "User created successfully. Your user ID is: " + str(user_id))
            self.create_user_window.destroy()  # Close the create user window
        else:
            messagebox.showerror("Registration Failed", "Unable to create user.")

class SavingsWindow:
    def __init__(self, database, user_id):
        self.database = database
        self.user_id = user_id
        self.window = tk.Tk()
        self.window.title("Savings")
        self.window.geometry("1200x1200")  # Adjust the size as needed
        self.create_widgets()
        self.window.mainloop()

    def create_widgets(self):
        # Menu bar setup
        menubar = Menu(self.window)
        self.window.config(menu=menubar)

        # Savings options menu
        savings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Savings Options", menu=savings_menu)
        savings_menu.add_command(label="Add a New Saving", command=self.add_new_saving)
        savings_menu.add_command(label="Delete a Saving", command=self.delete_saving)
        savings_menu.add_command(label="Edit a Saving", command=self.edit_saving)

        expense_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Expenses Options", menu=expense_menu)
        expense_menu.add_command(label="Add a New Expense", command=self.add_new_expense)
        expense_menu.add_command(label="Delete an Expense", command=self.delete_expense)
        expense_menu.add_command(label="Edit an Expense", command=self.edit_expense)

        # Option to go back to dashboard
        menubar.add_command(label="Back to Dashboard", command=self.back_to_dashboard)

        # Savings stats navigation
        menubar.add_command(label="Savings Stats", command=self.open_savings_stats)

        # Additional widgets for savings information here
        tk.Label(self.window, text="Savings Information", font=("Arial", 24)).pack(pady=20)
        # More widgets and functionality related to savings will be added here
        options_frame = tk.Frame(self.window)
        options_frame.pack(padx=10, pady=10)
        tk.Label(options_frame, text="Sort by:").grid(row=0, column=0, sticky='w')
        sort_by_var = tk.StringVar(self.window)
        sort_by_var.set('date')  # default value
        sort_by_menu = tk.OptionMenu(options_frame, sort_by_var, 'amount', 'date')
        sort_by_menu.grid(row=0, column=1, padx=5)

        tk.Label(options_frame, text="Order:").grid(row=0, column=2, sticky='w')
        sort_order_var = tk.StringVar(self.window)
        sort_order_var.set('asc')  # default value
        sort_order_menu = tk.OptionMenu(options_frame, sort_order_var, 'asc', 'desc')
        sort_order_menu.grid(row=0, column=3, padx=5)

        filter_var = tk.StringVar(self.window)
        filter_var.set('both')  # default value
        filter_menu = tk.OptionMenu(options_frame, filter_var, 'savings', 'expenses', 'both')
        filter_menu.grid(row=0, column=5, padx=5)

        refresh_button = tk.Button(options_frame, text="Refresh", command=lambda: self.refresh_data(sort_by_var.get(), sort_order_var.get(), filter_var.get()))
        refresh_button.grid(row=0, column=4, padx=5)

        # Treeview for displaying savings
        self.savings_tree = ttk.Treeview(self.window, columns=("Type", "ID", "Amount", "Purpose/Category", "Date"), show='headings')
        self.savings_tree.column("Type", width=60)  # New column for type
        self.savings_tree.column("ID", width=50)    # Adjust the width as needed
        self.savings_tree.column("Amount", width=100)  # Adjust the width as needed
        self.savings_tree.column("Purpose/Category", width=150) # Adjust the width as needed
        self.savings_tree.column("Date", width=100)    # Adjust the width as needed

        self.savings_tree.heading("Type", text="Type")
        self.savings_tree.heading("ID", text="ID")
        self.savings_tree.heading("Amount", text="Amount")
        self.savings_tree.heading("Purpose/Category", text="Purpose/Category")
        self.savings_tree.heading("Date", text="Date")

        self.savings_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # Initial loading of savings
        self.refresh_data("date", "asc", 'both')

    def refresh_data(self, sort_by, order, filter_type):
        for i in self.savings_tree.get_children():
            self.savings_tree.delete(i)  # Clear the treeview

        combined_data = []

        if filter_type in ['both', 'savings']:
            savings = self.database.get_user_savings(self.user_id, sort_by, order)
            for saving in savings:
                # Assuming saving tuple is in the format: (SavingsID, UserID, Amount, Purpose, Date)
                combined_data.append(('Saving', saving[0], saving[2], saving[3], saving[4]))

        if filter_type in ['both', 'expenses']:
            expenses = self.database.get_user_expenses(self.user_id, sort_by, order)
            for expense in expenses:
                # Assuming expense tuple is in the format: (ExpenseID, UserID, Amount, Category, Date)
                combined_data.append(('Expense', expense[0], expense[2], expense[3], expense[4]))

        # Sort the combined data
        sort_index = 4 if sort_by == 'date' else 2  # Adjust based on your sorting criteria
        combined_data.sort(key=lambda x: x[sort_index], reverse=(order == 'desc'))

        # Insert sorted data into the treeview
        for item in combined_data:
            self.savings_tree.insert('', tk.END, values=item, tags=(item[0].lower(),))

        self.savings_tree.tag_configure('saving', background='lightgreen')
        self.savings_tree.tag_configure('expense', background='lightcoral')


    def back_to_dashboard(self):
        self.window.destroy()  # Close the savings window
        DashboardWindow(self.database, self.user_id)  # Open the dashboard window
    def add_new_expense(self):
        add_window = Toplevel(self.window)
        add_window.title("Add New Expense")
        add_window.geometry("400x300")

        tk.Label(add_window, text="Amount:").grid(row=0, column=0, sticky='w')
        amount_entry = tk.Entry(add_window)
        amount_entry.grid(row=0, column=1)

        tk.Label(add_window, text="Purpose:").grid(row=1, column=0, sticky='w')
        purpose_entry = tk.Entry(add_window)
        purpose_entry.grid(row=1, column=1)

        submit_button = tk.Button(add_window, text="Submit",
                                  command=lambda: self.submit_add_new_expense(amount_entry.get(), purpose_entry.get(), add_window))
        submit_button.grid(row=2, column=1, pady=10)

    def submit_add_new_expense(self, amount, purpose, window):
        # Implement the logic to add a new saving to the database
        self.database.add_new_expense(self.user_id, amount, purpose)
        window.destroy()
        messagebox.showinfo("Success", "New expense added successfully.")

    def delete_expense(self):
        delete_window = Toplevel(self.window)
        delete_window.title("Delete expense")
        delete_window.geometry("400x300")

        tk.Label(delete_window, text="Expense ID:").grid(row=0, column=0, sticky='w')
        saving_id_entry = tk.Entry(delete_window)
        saving_id_entry.grid(row=0, column=1)

        submit_button = tk.Button(delete_window, text="Delete",
                                  command=lambda: self.submit_delete_expense(saving_id_entry.get(), delete_window))
        submit_button.grid(row=1, column=1, pady=10)

    def submit_delete_expense(self, expense_id, window):
        # Implement the logic to delete a saving from the database
        self.database.de(self.user_id, expense_id)
        window.destroy()
        messagebox.showinfo("Success", "Saving deleted successfully.")
    

    def edit_expense(self):
        edit_window = Toplevel(self.window)
        edit_window.title("Edit expense")
        edit_window.geometry("400x300")

        tk.Label(edit_window, text="Expense ID:").grid(row=0, column=0, sticky='w')
        saving_id_entry = tk.Entry(edit_window)
        saving_id_entry.grid(row=0, column=1)

        tk.Label(edit_window, text="New Amount:").grid(row=1, column=0, sticky='w')
        new_amount_entry = tk.Entry(edit_window)
        new_amount_entry.grid(row=1, column=1)

        tk.Label(edit_window, text="New Purpose:").grid(row=2, column=0, sticky='w')
        new_purpose_entry = tk.Entry(edit_window)
        new_purpose_entry.grid(row=2, column=1)

        submit_button = tk.Button(edit_window, text="Submit",
                                  command=lambda: self.submit_edit_expense(saving_id_entry.get(), new_amount_entry.get(), new_purpose_entry.get(), edit_window))
        submit_button.grid(row=3, column=1, pady=10)

    def submit_edit_expense(self, expense_id, new_amount, new_purpose, window):
        # Implement the logic to edit a saving in the database
        self.database.edit_expense(self.user_id, expense_id, new_amount, new_purpose)
        window.destroy()
        messagebox.showinfo("Success", "Saving edited successfully.")

    def add_new_saving(self):
        add_window = Toplevel(self.window)
        add_window.title("Add New Saving")
        add_window.geometry("400x300")

        tk.Label(add_window, text="Amount:").grid(row=0, column=0, sticky='w')
        amount_entry = tk.Entry(add_window)
        amount_entry.grid(row=0, column=1)

        tk.Label(add_window, text="Purpose:").grid(row=1, column=0, sticky='w')
        purpose_entry = tk.Entry(add_window)
        purpose_entry.grid(row=1, column=1)

        submit_button = tk.Button(add_window, text="Submit",
                                  command=lambda: self.submit_add_new_saving(amount_entry.get(), purpose_entry.get(), add_window))
        submit_button.grid(row=2, column=1, pady=10)

    def submit_add_new_saving(self, amount, purpose, window):
        # Implement the logic to add a new saving to the database
        self.database.add_new_saving(self.user_id, amount, purpose)
        window.destroy()
        messagebox.showinfo("Success", "New saving added successfully.")

    def delete_saving(self):
        delete_window = Toplevel(self.window)
        delete_window.title("Delete Saving")
        delete_window.geometry("400x300")

        tk.Label(delete_window, text="Saving ID:").grid(row=0, column=0, sticky='w')
        saving_id_entry = tk.Entry(delete_window)
        saving_id_entry.grid(row=0, column=1)

        submit_button = tk.Button(delete_window, text="Delete",
                                  command=lambda: self.submit_delete_saving(saving_id_entry.get(), delete_window))
        submit_button.grid(row=1, column=1, pady=10)

    def submit_delete_saving(self, saving_id, window):
        # Implement the logic to delete a saving from the database
        self.database.delete_saving(self.user_id, saving_id)
        window.destroy()
        messagebox.showinfo("Success", "Saving deleted successfully.")

    def edit_saving(self):
        edit_window = Toplevel(self.window)
        edit_window.title("Edit Saving")
        edit_window.geometry("400x300")

        tk.Label(edit_window, text="Saving ID:").grid(row=0, column=0, sticky='w')
        saving_id_entry = tk.Entry(edit_window)
        saving_id_entry.grid(row=0, column=1)

        tk.Label(edit_window, text="New Amount:").grid(row=1, column=0, sticky='w')
        new_amount_entry = tk.Entry(edit_window)
        new_amount_entry.grid(row=1, column=1)

        tk.Label(edit_window, text="New Purpose:").grid(row=2, column=0, sticky='w')
        new_purpose_entry = tk.Entry(edit_window)
        new_purpose_entry.grid(row=2, column=1)

        submit_button = tk.Button(edit_window, text="Submit",
                                  command=lambda: self.submit_edit_saving(saving_id_entry.get(), new_amount_entry.get(), new_purpose_entry.get(), edit_window))
        submit_button.grid(row=3, column=1, pady=10)

    def submit_edit_saving(self, saving_id, new_amount, new_purpose, window):
        # Implement the logic to edit a saving in the database
        self.database.edit_saving(self.user_id, saving_id, new_amount, new_purpose)
        window.destroy()
        messagebox.showinfo("Success", "Saving edited successfully.")
    
    def open_savings_stats(self):
        self.window.destroy()  # Close the savings window
        SavingsStatsWindow(self.database, self.user_id)

class SavingsStatsWindow:
    def __init__(self, database, user_id):
        self.database = database
        self.user_id = user_id
        self.window = tk.Tk()
        self.window.title("Savings")
        self.window.geometry("1200x1200")  # Adjust the size as needed
        self.create_widgets()
        self.window.mainloop()

    def create_widgets(self):
        # Menu bar setup
        menubar = Menu(self.window)
        self.window.config(menu=menubar)

        # Savings options menu
        savings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Savings Options", menu=savings_menu)
        savings_menu.add_command(label="Add a New Saving", command=self.add_new_saving)
        savings_menu.add_command(label="Delete a Saving", command=self.delete_saving)
        savings_menu.add_command(label="Edit a Saving", command=self.edit_saving)

        expense_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Expenses Options", menu=expense_menu)
        expense_menu.add_command(label="Add a New Expense", command=self.add_new_expense)
        expense_menu.add_command(label="Delete an Expense", command=self.delete_expense)
        expense_menu.add_command(label="Edit an Expense", command=self.edit_expense)

        # Option to go back to dashboard
        menubar.add_command(label="Back to Dashboard", command=self.back_to_dashboard)

        # Savings stats navigation
        menubar.add_command(label="Savings Info", command=self.open_savings_info)

        tk.Label(self.window, text="Savings Stats", font=("Arial", 24)).pack(pady=20)

        total_savings = self.database.get_total_savings(self.user_id)
        total_expenses = self.database.get_total_expenses(self.user_id)
        net_worth = total_savings - total_expenses
        highest_lowest_savings = self.database.get_highest_and_lowest_savings(self.user_id)
        highest_lowest_expenses = self.database.get_highest_and_lowest_expenses(self.user_id)
        number_of_savings_entries = self.database.get_number_of_savings_entries(self.user_id)
        number_of_expenses_entries = self.database.get_number_of_expenses_entries(self.user_id)

        stats_frame = tk.Frame(self.window)
        stats_frame.pack(pady=10)

        tk.Label(stats_frame, text=f"Total Savings: ${total_savings}", font=("Arial", 14)).pack()
        tk.Label(stats_frame, text=f"Total Expenses: ${total_expenses}", font=("Arial", 14)).pack()
        tk.Label(stats_frame, text=f"Net Worth: ${net_worth}", font=("Arial", 14)).pack()
        tk.Label(stats_frame, text=f"Highest Savings: ${highest_lowest_savings[0]}", font=("Arial", 14)).pack()
        tk.Label(stats_frame, text=f"Lowest Savings: ${highest_lowest_savings[1]}", font=("Arial", 14)).pack()
        tk.Label(stats_frame, text=f"Highest Expenses: ${highest_lowest_expenses[0]}", font=("Arial", 14)).pack()
        tk.Label(stats_frame, text=f"Lowest Expenses: ${highest_lowest_expenses[1]}", font=("Arial", 14)).pack()
        tk.Label(stats_frame, text=f"Number of Savings Entries: {number_of_savings_entries}", font=("Arial", 14)).pack()
        tk.Label(stats_frame, text=f"Number of Expenses Entries: {number_of_expenses_entries}", font=("Arial", 14)).pack()

        self.plot_savings_expenses_trends()

    def plot_savings_expenses_trends(self):
        data = self.database.get_savings_expenses_over_time(self.user_id)
        # Assuming data is in the format [(date1, savings1, expenses1), (date2, savings2, expenses2), ...]

        # If dates are already datetime.date objects, no conversion is needed
        dates = [record[0] for record in data]
        savings = [record[1] for record in data]
        expenses = [record[2] for record in data]

        fig, ax = plt.subplots()

        # Plotting
        ax.plot(dates, savings, label='Savings', color='green')
        ax.plot(dates, expenses, label='Expenses', color='red')

        # Formatting the date to make it more readable
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        plt.xticks(rotation=45)

        # Adding labels and title
        ax.set_xlabel('Date')
        ax.set_ylabel('Amount')
        ax.set_title('Savings and Expenses Over Time')
        ax.legend()

        # Adjust layout
        plt.tight_layout()

        # Embedding the plot into the Tkinter window
        canvas = FigureCanvasTkAgg(fig, master=self.window)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(expand=True, fill='both')
        canvas.draw()
       
    def back_to_dashboard(self):
        self.window.destroy()  # Close the savings window
        DashboardWindow(self.database, self.user_id)  # Open the dashboard window

    def add_new_saving(self):
        add_window = Toplevel(self.window)
        add_window.title("Add New Saving")
        add_window.geometry("400x300")

        tk.Label(add_window, text="Amount:").grid(row=0, column=0, sticky='w')
        amount_entry = tk.Entry(add_window)
        amount_entry.grid(row=0, column=1)

        tk.Label(add_window, text="Purpose:").grid(row=1, column=0, sticky='w')
        purpose_entry = tk.Entry(add_window)
        purpose_entry.grid(row=1, column=1)

        submit_button = tk.Button(add_window, text="Submit",
                                  command=lambda: self.submit_add_new_saving(amount_entry.get(), purpose_entry.get(), add_window))
        submit_button.grid(row=2, column=1, pady=10)

    def submit_add_new_saving(self, amount, purpose, window):
        # Implement the logic to add a new saving to the database
        self.database.add_new_saving(self.user_id, amount, purpose)
        window.destroy()
        messagebox.showinfo("Success", "New saving added successfully.")

    def delete_saving(self):
        delete_window = Toplevel(self.window)
        delete_window.title("Delete Saving")
        delete_window.geometry("400x300")

        tk.Label(delete_window, text="Saving ID:").grid(row=0, column=0, sticky='w')
        saving_id_entry = tk.Entry(delete_window)
        saving_id_entry.grid(row=0, column=1)

        submit_button = tk.Button(delete_window, text="Delete",
                                  command=lambda: self.submit_delete_saving(saving_id_entry.get(), delete_window))
        submit_button.grid(row=1, column=1, pady=10)

    def submit_delete_saving(self, saving_id, window):
        # Implement the logic to delete a saving from the database
        self.database.delete_saving(self.user_id, saving_id)
        window.destroy()
        messagebox.showinfo("Success", "Saving deleted successfully.")

    def edit_saving(self):
        edit_window = Toplevel(self.window)
        edit_window.title("Edit Saving")
        edit_window.geometry("400x300")

        tk.Label(edit_window, text="Saving ID:").grid(row=0, column=0, sticky='w')
        saving_id_entry = tk.Entry(edit_window)
        saving_id_entry.grid(row=0, column=1)

        tk.Label(edit_window, text="New Amount:").grid(row=1, column=0, sticky='w')
        new_amount_entry = tk.Entry(edit_window)
        new_amount_entry.grid(row=1, column=1)

        tk.Label(edit_window, text="New Purpose:").grid(row=2, column=0, sticky='w')
        new_purpose_entry = tk.Entry(edit_window)
        new_purpose_entry.grid(row=2, column=1)

        submit_button = tk.Button(edit_window, text="Submit",
                                  command=lambda: self.submit_edit_saving(saving_id_entry.get(), new_amount_entry.get(), new_purpose_entry.get(), edit_window))
        submit_button.grid(row=3, column=1, pady=10)

    def submit_edit_saving(self, saving_id, new_amount, new_purpose, window):
        # Implement the logic to edit a saving in the database
        self.database.edit_saving(self.user_id, saving_id, new_amount, new_purpose)
        window.destroy()
        messagebox.showinfo("Success", "Saving edited successfully.")
    
    def add_new_expense(self):
        add_window = Toplevel(self.window)
        add_window.title("Add New Expense")
        add_window.geometry("400x300")

        tk.Label(add_window, text="Amount:").grid(row=0, column=0, sticky='w')
        amount_entry = tk.Entry(add_window)
        amount_entry.grid(row=0, column=1)

        tk.Label(add_window, text="Purpose:").grid(row=1, column=0, sticky='w')
        purpose_entry = tk.Entry(add_window)
        purpose_entry.grid(row=1, column=1)

        submit_button = tk.Button(add_window, text="Submit",
                                  command=lambda: self.submit_add_new_expense(amount_entry.get(), purpose_entry.get(), add_window))
        submit_button.grid(row=2, column=1, pady=10)

    def submit_add_new_expense(self, amount, purpose, window):
        # Implement the logic to add a new saving to the database
        self.database.add_new_expense(self.user_id, amount, purpose)
        window.destroy()
        messagebox.showinfo("Success", "New expense added successfully.")

    def delete_expense(self):
        delete_window = Toplevel(self.window)
        delete_window.title("Delete expense")
        delete_window.geometry("400x300")

        tk.Label(delete_window, text="Expense ID:").grid(row=0, column=0, sticky='w')
        saving_id_entry = tk.Entry(delete_window)
        saving_id_entry.grid(row=0, column=1)

        submit_button = tk.Button(delete_window, text="Delete",
                                  command=lambda: self.submit_delete_expense(saving_id_entry.get(), delete_window))
        submit_button.grid(row=1, column=1, pady=10)

    def submit_delete_expense(self, expense_id, window):
        # Implement the logic to delete a saving from the database
        self.database.de(self.user_id, expense_id)
        window.destroy()
        messagebox.showinfo("Success", "Saving deleted successfully.")
    

    def edit_expense(self):
        edit_window = Toplevel(self.window)
        edit_window.title("Edit expense")
        edit_window.geometry("400x300")

        tk.Label(edit_window, text="Expense ID:").grid(row=0, column=0, sticky='w')
        saving_id_entry = tk.Entry(edit_window)
        saving_id_entry.grid(row=0, column=1)

        tk.Label(edit_window, text="New Amount:").grid(row=1, column=0, sticky='w')
        new_amount_entry = tk.Entry(edit_window)
        new_amount_entry.grid(row=1, column=1)

        tk.Label(edit_window, text="New Purpose:").grid(row=2, column=0, sticky='w')
        new_purpose_entry = tk.Entry(edit_window)
        new_purpose_entry.grid(row=2, column=1)

        submit_button = tk.Button(edit_window, text="Submit",
                                  command=lambda: self.submit_edit_expense(saving_id_entry.get(), new_amount_entry.get(), new_purpose_entry.get(), edit_window))
        submit_button.grid(row=3, column=1, pady=10)

    def submit_edit_expense(self, expense_id, new_amount, new_purpose, window):
        # Implement the logic to edit a saving in the database
        self.database.edit_expense(self.user_id, expense_id, new_amount, new_purpose)
        window.destroy()
        messagebox.showinfo("Success", "Saving edited successfully.")

    def open_savings_info(self):
        self.window.destroy()  # Close the dashboard window
        SavingsWindow(self.database, self.user_id)


class ChallengesWindow:
    def __init__(self, database, user_id):
        self.database = database
        self.user_id = user_id
        self.challenge_id_map = {}

        self.window = tk.Tk()
        self.window.title("Challenges")
        self.window.geometry("800x600")

        self.create_layout()
        self.refresh_challenges()
        self.window.mainloop()

    def create_add_challenge_button(self):
        add_challenge_button = tk.Button(self.window, text="Add Challenge", command=self.open_add_challenge_window)
        add_challenge_button.pack(anchor='nw', padx=10, pady=10)

    def create_return_dashboard_button(self):
        return_button = tk.Button(self.window, text="Return to Dashboard", command=self.return_to_dashboard)
        return_button.pack(anchor='ne', padx=10, pady=10)

    def return_to_dashboard(self):
        self.window.destroy()
        DashboardWindow(self.database, self.user_id)

    def create_layout(self):
        top_frame = tk.Frame(self.window)
        top_frame.pack(side='top', fill='x')

        # Add Challenge button
        add_challenge_button = tk.Button(top_frame, text="Add Challenge", command=self.open_add_challenge_window)
        add_challenge_button.pack(side='left', padx=10, pady=10)

        # Return to Dashboard button
        return_button = tk.Button(top_frame, text="Return to Dashboard", command=self.return_to_dashboard)
        return_button.pack(side='right', padx=10, pady=10)

        # Challenges Treeview
        self.challenges_tree = ttk.Treeview(self.window, columns=("Name", "TargetAmount", "CurrentAmount"), show='headings')
        self.challenges_tree.heading("Name", text="Name")
        self.challenges_tree.heading("TargetAmount", text="Target Amount")
        self.challenges_tree.heading("CurrentAmount", text="Amount Saved")
        self.challenges_tree.column("Name", width=200)
        self.challenges_tree.column("TargetAmount", width=150)
        self.challenges_tree.column("CurrentAmount", width=150)
        self.challenges_tree.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        # Edit Challenge button (initially hidden)
        self.edit_button = tk.Button(self.window, text="View/Edit Challenge", command=self.edit_selected_challenge)
        self.edit_button.pack_forget()

        # Bind selection event
        self.challenges_tree.bind("<<TreeviewSelect>>", self.on_challenge_select)



    def on_challenge_select(self, event):
        selected = self.challenges_tree.selection()
        if selected:
            self.edit_button.pack(side='top', pady=10)
        else:
            self.edit_button.pack_forget()

    def refresh_challenges(self):
        self.challenge_id_map.clear()  # Clear the existing mapping
        for item in self.challenges_tree.get_children():
            self.challenges_tree.delete(item)

        challenges = self.database.get_user_challenges(self.user_id)
        for challenge in challenges:
            tree_item = self.challenges_tree.insert('', 'end', values=(challenge[1], challenge[5], challenge[6]))
            self.challenge_id_map[tree_item] = challenge[0]  # Map the Treeview item to the ChallengeID



    def open_add_challenge_window(self):
        AddChallengeWindow(self.database, self.user_id, self.refresh_challenges)

    def on_challenge_select(self, event):
        selected = self.challenges_tree.selection()
        if selected:
            item = selected[0]
            self.selected_challenge_id = self.challenge_id_map[item]  # Store selected ChallengeID
            self.edit_button.pack(side='top', pady=10)

            # Debugging message
            print(f"Selected Challenge ID: {self.selected_challenge_id}")
        else:
            self.edit_button.pack_forget()

class AddChallengeWindow:
    def __init__(self, database, user_id, refresh_callback):
        self.database = database
        self.user_id = user_id
        self.refresh_callback = refresh_callback
        self.add_window = tk.Toplevel()
        self.add_window.title("Add New Challenge")
        self.add_window.geometry("400x500")
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.add_window, text="Name:").grid(row=0, column=0, sticky='w')
        self.name_entry = tk.Entry(self.add_window)
        self.name_entry.grid(row=0, column=1)

        tk.Label(self.add_window, text="Description:").grid(row=1, column=0, sticky='nw')
        self.description_text = tk.Text(self.add_window, height=10, width=30)
        self.description_text.grid(row=1, column=1, sticky='w')

        tk.Label(self.add_window, text="End Date (YYYY-MM-DD):").grid(row=2, column=0, sticky='w')
        self.end_date_entry = tk.Entry(self.add_window)
        self.end_date_entry.grid(row=2, column=1)

        tk.Label(self.add_window, text="Target Amount:").grid(row=3, column=0, sticky='w')
        self.target_amount_entry = tk.Entry(self.add_window)
        self.target_amount_entry.grid(row=3, column=1)

        submit_button = tk.Button(self.add_window, text="Submit", command=self.submit_challenge)
        submit_button.grid(row=4, column=1, pady=10)

    def submit_challenge(self):
        name = self.name_entry.get()
        description = self.description_text.get("1.0", tk.END).strip()
        end_date = self.end_date_entry.get()
        target_amount = self.target_amount_entry.get()

        # Call the method with the required arguments
        self.database.add_new_challenge(name, description, end_date, target_amount, self.user_id)

        # Close the window and refresh the challenge list
        self.add_window.destroy()
        self.refresh_callback()

class EditChallengeWindow:
    def __init__(self, database, user_id, challenge_id, refresh_callback, name, target_amount, current_amount):
        self.database = database
        self.user_id = user_id
        self.challenge_id = challenge_id


        self.refresh_callback = refresh_callback
        self.edit_window = tk.Toplevel()
        self.edit_window.title("Edit Challenge")
        self.edit_window.geometry("500x300")

        self.create_widgets(name, target_amount, current_amount)

    def create_widgets(self, name, target_amount, current_amount):
        tk.Label(self.edit_window, text=f"Challenge: {name}").grid(row=0, column=0, sticky='w')
        tk.Label(self.edit_window, text=f"Target: {target_amount}").grid(row=1, column=0, sticky='w')
        tk.Label(self.edit_window, text=f"Saved: {current_amount}").grid(row=2, column=0, sticky='w')

        delete_button = tk.Button(self.edit_window, text="Delete Challenge", command=self.delete_challenge)
        delete_button.grid(row=3, column=0, pady=5)

        self.amount_entry = tk.Entry(self.edit_window)
        self.amount_entry.grid(row=4, column=0)


        move_money_button = tk.Button(self.edit_window, text="Move Money to Challenge", command=self.move_money_to_challenge)
        move_money_button.grid(row=5, column=0, pady=5)

    def delete_challenge(self):
        self.database.delete_challenge(self.challenge_id)
        self.edit_window.destroy()
        self.refresh_callback()

    def move_money_to_challenge(self):
        amount = float(self.amount_entry.get())
        if self.database.move_money_to_challenge(self.user_id, self.challenge_id, amount):
            messagebox.showinfo("Success", "Money moved to challenge successfully.")
            self.edit_window.destroy()
            self.refresh_callback()
        else:
            messagebox.showwarning("Insufficient Savings", "You do not have enough savings to complete this transaction.")
class DashboardWindow:
    def __init__(self, database, user_id):
        self.database = database
        self.user_id = user_id
        self.dashboard = tk.Tk()
        self.dashboard.title("Dashboard")
        self.dashboard.geometry("800x600")

        self.create_widgets()
        self.dashboard.mainloop()

    def create_widgets(self):
        user_info = self.database.get_user_info(self.user_id)
        if user_info is None:
            messagebox.showerror("Error", "Unable to retrieve user information.")
            return

        # Add logout dropdown menu
        def logout():
            response = messagebox.askyesno("Logout", "Are you sure you want to log out?")
            if response:
                self.dashboard.destroy()  # Close the dashboard window
                open_login_window()# Open the login window

        # Create a menubar
        menubar = Menu(self.dashboard)
        self.dashboard.config(menu=menubar)

        # Create a menu
        user_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label=f"{user_info[1]} {user_info[2]}", menu=user_menu)
        user_menu.add_command(label="Log out", command=logout)

        # Welcome label
        welcome_label = tk.Label(self.dashboard, text=f"Welcome {user_info[1]}", font=("Arial", 24), bg="#FFDAB9")
        welcome_label.pack(pady=20, fill='x')

        # Button style configuration
        button_style = {'font': ("Arial", 16), 'border': 0, 'bg': "#FFA07A", 'activebackground': "#FF7F50", 'padx': 10, 'pady': 5}

        # View Savings Button
        view_savings_button = tk.Button(self.dashboard, text="View Savings", **button_style, command=self.open_savings_window)
        view_savings_button.pack(pady=10, ipadx=50, ipady=10)

        # View Goals Button
        view_goals_button = tk.Button(self.dashboard, text="View Challenges", **button_style, command=self.open_challenges_window)
        view_goals_button.pack(pady=10, ipadx=50, ipady=10)

        # View Projections Button
        view_projections_button = tk.Button(self.dashboard, text="View Projections", **button_style)
        view_projections_button.pack(pady=10, ipadx=50, ipady=10)

        # Inbox Button
        leader_button = tk.Button(self.dashboard, text="Leader Board", **button_style, command=self.open_leaderboard_window)
        leader_button.pack(pady=10, ipadx=50, ipady=10)

        leader_button = tk.Button(self.dashboard, text="View Groups", **button_style, command=self.open_groups_window)
        leader_button.pack(pady=10, ipadx=50, ipady=10)

    def open_groups_window(self):
        self.dashboard.destroy()
        GroupWindow(self.database, self.user_id)

    def open_leaderboard_window(self):
        self.dashboard.destroy()
        OverallPlacementWindow(self.database, self.user_id)

    def open_savings_window(self):
        self.dashboard.destroy()  # Close the dashboard window
        SavingsWindow(self.database, self.user_id)  # Open the savings window

    def open_challenges_window(self):
        self.dashboard.destroy()  # Close the dashboard window
        ChallengesWindow(self.database, self.user_id)  # Open the challenges window

class GroupWindow:
    def __init__(self, database, user_id):
        self.database = database
        self.user_id = user_id
        self.window = tk.Tk()
        self.window.title("Goals View")
        self.window.geometry("1200x1200")  # Adjust the size as needed

        self.create_widgets()
        self.display_goals()
        self.window.mainloop()

    def create_widgets(self):
        # Menu bar setup
        menubar = Menu(self.window)
        self.window.config(menu=menubar)
        menubar.add_command(label="Back to Dashboard", command=self.back_to_dashboard)
        menubar.add_command(label="Select New Group", command=self.get_new_groups)
        group_management_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Group Management", menu=group_management_menu)
        group_management_menu.add_command(label="Create Group", command=self.create_group)
        group_management_menu.add_command(label="Edit Group", command=self.edit_group)
        group_management_menu.add_command(label="Delete Group", command=self.delete_group)

        tk.Label(self.window, text="Group View", font=("Arial", 24)).pack(pady=20)

        # Treeview for displaying goals
        self.goals_tree = ttk.Treeview(self.window, columns=('GroupID', 'GroupName', 'GroupGoal', 'CurrentSavings'), show='headings')
        self.goals_tree.heading('GroupID', text='Group ID')
        self.goals_tree.heading('GroupName', text='Group Name')
        self.goals_tree.heading('GroupGoal', text='Goal Amount')
        self.goals_tree.heading('CurrentSavings', text='Current Savings')
        self.goals_tree.column('GroupID', width=100)
        self.goals_tree.column('GroupName', width=200)
        self.goals_tree.column('GroupGoal', width=100)
        self.goals_tree.column('CurrentSavings', width=100)
        self.goals_tree.bind('<<TreeviewSelect>>', self.on_goal_select)
        self.goals_tree.pack(expand=True, fill='both')

    def display_goals(self):
        try:
            group_goals = self.database.get_group_goals(self.user_id)
            for goal in group_goals:
                # Each 'goal' should have GroupID, GroupName, GroupGoal, CurrentGroupSavings
                self.goals_tree.insert('', 'end', values=goal)
        except Exception as e:
            tk.messagebox.showerror("Error", f"An error occurred while fetching goals: {e}")

    def clear_treeview(self):
        for item in self.goals_tree.get_children():
            self.goals_tree.delete(item)

    def on_goal_select(self, event):
        selected_item = self.goals_tree.selection()[0]
        group_id = self.goals_tree.item(selected_item)['values'][0]
        self.add_contribution(group_id)

    def add_contribution(self, group_id):
        amount = simpledialog.askfloat("Contribution", f"Enter contribution amount for {self.database.get_group_name(group_id)}:", parent=self.window)
        if amount is not None:
            try:
                self.database.add_contribution_to_group(group_id, amount)
                tk.messagebox.showinfo("Success", "Contribution added successfully")

                # Refresh the TreeView
                self.clear_treeview()
                self.display_goals()

            except Exception as e:
                tk.messagebox.showerror("Error", f"An error occurred: {e}")

    def get_new_groups(self):
        self.window.destroy()  # Close the savings window
        SelectGroupWindow(self.database, self.user_id)


    def back_to_dashboard(self):
        self.window.destroy()  # Close the savings window
        DashboardWindow(self.database, self.user_id)

    def create_group(self):
        def submit():
            group_name = name_entry.get()
            description = desc_entry.get()
            group_goal = goal_entry.get()
            # Validate inputs...

            try:
                self.database.create_group(self.user_id, group_name, description, group_goal)
                tk.messagebox.showinfo("Success", "Group created successfully")
                create_window.destroy()
                self.clear_treeview()
                self.display_goals()
            except Exception as e:
                tk.messagebox.showerror("Error", f"An error occurred: {e}")

        create_window = Toplevel(self.window)
        create_window.title("Create Group")
        create_window.geometry("400x300")

        tk.Label(create_window, text="Group Name:").grid(row=0, column=0)
        name_entry = tk.Entry(create_window)
        name_entry.grid(row=0, column=1)

        tk.Label(create_window, text="Description:").grid(row=1, column=0)
        desc_entry = tk.Entry(create_window)
        desc_entry.grid(row=1, column=1)

        tk.Label(create_window, text="Group Goal:").grid(row=2, column=0)
        goal_entry = tk.Entry(create_window)
        goal_entry.grid(row=2, column=1)

        submit_button = tk.Button(create_window, text="Create Group", command=submit)
        submit_button.grid(row=3, column=1)

    def edit_group(self):
        selected_item = self.goals_tree.selection()
        if not selected_item:
            tk.messagebox.showwarning("Warning", "No group selected")
            return

        group_id = self.goals_tree.item(selected_item[0])['values'][0]

        def submit():
            new_group_name = name_entry.get()
            new_description = desc_entry.get()
            new_group_goal = goal_entry.get()
            # Validate inputs...

            try:
                self.database.edit_group(self.user_id, group_id, new_group_name, new_description, new_group_goal)
                tk.messagebox.showinfo("Success", "Group updated successfully")
                edit_window.destroy()
                self.clear_treeview()
                self.display_goals()
            except Exception as e:
                tk.messagebox.showerror("Error", f"An error occurred: {e}")

        edit_window = Toplevel(self.window)
        edit_window.title("Edit Group")
        edit_window.geometry("400x300")

        tk.Label(edit_window, text="New Group Name:").grid(row=0, column=0)
        name_entry = tk.Entry(edit_window)
        name_entry.grid(row=0, column=1)

        tk.Label(edit_window, text="New Description:").grid(row=1, column=0)
        desc_entry = tk.Entry(edit_window)
        desc_entry.grid(row=1, column=1)

        tk.Label(edit_window, text="New Group Goal:").grid(row=2, column=0)
        goal_entry = tk.Entry(edit_window)
        goal_entry.grid(row=2, column=1)

        submit_button = tk.Button(edit_window, text="Update Group", command=submit)
        submit_button.grid(row=3, column=1)
        
    def delete_group(self):
        selected_item = self.goals_tree.selection()
        if not selected_item:
            tk.messagebox.showwarning("Warning", "No group selected")
            return

        group_id = self.goals_tree.item(selected_item[0])['values'][0]
        group_name = self.goals_tree.item(selected_item[0])['values'][1]

        if tk.messagebox.askyesno("Delete Group", f"Are you sure you want to delete the group '{group_name}'?"):
            try:
                self.database.delete_group(self.user_id, group_id)
                tk.messagebox.showinfo("Success", "Group deleted successfully")
                self.clear_treeview()
                self.display_goals()
            except Exception as e:
                tk.messagebox.showerror("Error", f"An error occurred: {e}")

class SelectGroupWindow:
    def __init__(self, database, user_id):
        self.database = database
        self.user_id = user_id
        self.window = tk.Tk()
        self.window.title("Goals Select")
        self.window.geometry("1200x1200")  # Adjust the size as needed

        self.create_widgets()
        self.display_goals()
        self.window.mainloop()

    def create_widgets(self):
        # Menu bar setup
        menubar = Menu(self.window)
        self.window.config(menu=menubar)
        menubar.add_command(label="Back to Dashboard", command=self.back_to_dashboard)
        menubar.add_command(label="View Your Groups", command=self.View_your_groups_window)


        tk.Label(self.window, text="Group View", font=("Arial", 24)).pack(pady=20)

        # Treeview for displaying goals
        self.goals_tree = ttk.Treeview(self.window, columns=('GroupID', 'GroupName', 'Description', 'GroupGoal', 'NumUsers'), show='headings')
        self.goals_tree.heading('GroupID', text='Group ID')
        self.goals_tree.heading('GroupName', text='Group Name')
        self.goals_tree.heading('Description', text='Description')
        self.goals_tree.heading('GroupGoal', text='Goal Amount')
        self.goals_tree.heading('NumUsers', text='Number of Users')

        self.goals_tree.column('GroupID', width=100)
        self.goals_tree.column('GroupName', width=200)
        self.goals_tree.column('Description', width=300)
        self.goals_tree.column('GroupGoal', width=100)
        self.goals_tree.column('NumUsers', width=100)
        self.goals_tree.bind('<<TreeviewSelect>>', self.on_goal_select)
        self.goals_tree.pack(expand=True, fill='both')


    def display_goals(self):
        try:
            groups = self.database.get_groups_user_not_member_of(self.user_id)
            for group in groups:
                # Each 'group' should have GroupID, GroupName, Description, GroupGoal, NumUsers
                self.goals_tree.insert('', 'end', values=group)
        except Exception as e:
            tk.messagebox.showerror("Error", f"An error occurred while fetching groups: {e}")

    def clear_treeview(self):
        for item in self.goals_tree.get_children():
            self.goals_tree.delete(item)

    def on_goal_select(self, event):
        selected_item = self.goals_tree.selection()[0]
        group_id = self.goals_tree.item(selected_item)['values'][0]
        group_name = self.goals_tree.item(selected_item)['values'][1]

        if tk.messagebox.askyesno("Join Group", f"Do you want to join the group '{group_name}'?"):
            try:
                self.database.add_user_to_group(self.user_id, group_id)
                tk.messagebox.showinfo("Success", f"You have successfully joined the group '{group_name}'")

                # Refresh the TreeView
                self.clear_treeview()
                self.display_goals()

            except Exception as e:
                tk.messagebox.showerror("Error", f"An error occurred: {e}")

    def View_your_groups_window(self):
        self.window.destroy()
        GroupWindow(self.database, self.user_id)


    def back_to_dashboard(self):
        self.window.destroy()  # Close the savings window
        DashboardWindow(self.database, self.user_id)

class SavingsLeaderboardWindow:
    def __init__(self, database, user_id):
        self.database = database
        self.user_id = user_id
        self.window = tk.Tk()
        self.window.title("Savings Leaderboard")
        self.window.geometry("1200x1200")  # Adjust the size as needed

        self.create_widgets()
        self.load_leaderboard_data("all")
        self.window.mainloop()
    def create_widgets(self):
        menubar = Menu(self.window)
        self.window.config(menu=menubar)

        # Leaderboard options menu
        leaderboard_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Leaderboard Options", menu=leaderboard_menu)
        leaderboard_menu.add_command(label="Overall Placement", command=self.overall_placement)
        leaderboard_menu.add_command(label="Expenses Leaderboard", command=self.expenses_leaderboard)
        leaderboard_menu.add_command(label="Net Worth Leaderboard", command=self.net_worth_leaderboard)
        
        menubar.add_command(label="Back to Dashboard", command=self.back_to_dashboard)
        # Leaderboard label
        tk.Label(self.window, text="Savings Leaderboard", font=("Arial", 24)).pack(pady=20)

        # Buttons for leaderboard limits
        buttons_frame = tk.Frame(self.window)
        buttons_frame.pack(pady=10)
        tk.Button(buttons_frame, text="Top 10", command=lambda: self.load_leaderboard_data("top10")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Top 50", command=lambda: self.load_leaderboard_data("top50")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Top 100", command=lambda: self.load_leaderboard_data("top100")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Show All", command=lambda: self.load_leaderboard_data("all")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Refresh", command=lambda: self.load_leaderboard_data("all")).pack(side=tk.RIGHT)

        # Treeview for displaying leaderboard
        self.leaderboard_tree = ttk.Treeview(self.window, columns=("Rank", "UserID", "FirstName", "LastName", "TotalSavings"), show='headings')
        self.leaderboard_tree.column("Rank", width=50)
        self.leaderboard_tree.column("UserID", width=100)
        self.leaderboard_tree.column("FirstName", width=150)
        self.leaderboard_tree.column("LastName", width=150)
        self.leaderboard_tree.column("TotalSavings", width=150)

        self.leaderboard_tree.heading("Rank", text="Rank")
        self.leaderboard_tree.heading("UserID", text="UserID")
        self.leaderboard_tree.heading("FirstName", text="First Name")
        self.leaderboard_tree.heading("LastName", text="Last Name")
        self.leaderboard_tree.heading("TotalSavings", text="Total Savings")

        self.leaderboard_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    def load_leaderboard_data(self, limit):
        # Clear the treeview
        for i in self.leaderboard_tree.get_children():
            self.leaderboard_tree.delete(i)

        # Fetch leaderboard data from the database
        leaderboard_data = self.database.get_savings_leaderboard_data()

        # Sort the data based on TotalSavings in descending order
        sorted_data = sorted(leaderboard_data, key=lambda x: x[-1], reverse=True)

        # Apply limit
        if limit == "top10":
            sorted_data = sorted_data[:10]
        elif limit == "top50":
            sorted_data = sorted_data[:50]
        elif limit == "top100":
            sorted_data = sorted_data[:100]
        # 'all' will show all entries

        # Insert sorted data into the treeview
        for index, item in enumerate(sorted_data, start=1):
            self.leaderboard_tree.insert('', tk.END, values=(index,) + item)

    # Placeholder methods for menu commands
    def back_to_dashboard(self):
        self.window.destroy()  # Close the savings window
        DashboardWindow(self.database, self.user_id)

    def overall_placement(self):
        self.window.destroy()
        OverallPlacementWindow(self.database, self.user_id)  # Implement the functionality

    def expenses_leaderboard(self):
        self.window.destroy()
        ExpenseLeaderboardWindow(self.database, self.user_id)  # Implement the functionality

    def net_worth_leaderboard(self):
        self.window.destroy()
        NetWorthLeaderboardWindow(self.database, self.user_id)


class ExpenseLeaderboardWindow:
    def __init__(self, database, user_id):
        self.database = database
        self.user_id = user_id
        self.window = tk.Tk()
        self.window.title("Expense Leaderboard")
        self.window.geometry("1200x1200")  # Adjust the size as needed

        self.create_widgets()
        self.load_leaderboard_data("all")
        self.window.mainloop()

    def create_widgets(self):
        # Menu bar setup
        menubar = Menu(self.window)
        self.window.config(menu=menubar)

        # Leaderboard options menu
        leaderboard_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Leaderboard Options", menu=leaderboard_menu)
        leaderboard_menu.add_command(label="Overall Placement", command=self.overall_placement)
        leaderboard_menu.add_command(label="Savings Leaderboard", command=self.savings_leaderboard)
        leaderboard_menu.add_command(label="Net Worth Leaderboard", command=self.net_worth_leaderboard)

        menubar.add_command(label="Back to Dashboard", command=self.back_to_dashboard)
        # Leaderboard label
        tk.Label(self.window, text="Big Spenders", font=("Arial", 24)).pack(pady=20)

        # Buttons for leaderboard limits
        buttons_frame = tk.Frame(self.window)
        buttons_frame.pack(pady=10)
        tk.Button(buttons_frame, text="Top 10", command=lambda: self.load_leaderboard_data("top10")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Top 50", command=lambda: self.load_leaderboard_data("top50")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Top 100", command=lambda: self.load_leaderboard_data("top100")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Show All", command=lambda: self.load_leaderboard_data("all")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Refresh", command=lambda: self.load_leaderboard_data("all")).pack(side=tk.RIGHT)

        self.leaderboard_tree = ttk.Treeview(self.window, columns=("Rank", "UserID", "FirstName", "LastName", "TotalExpense"), show='headings')
        self.leaderboard_tree.column("Rank", width=50)
        self.leaderboard_tree.column("UserID", width=100)
        self.leaderboard_tree.column("FirstName", width=150)
        self.leaderboard_tree.column("LastName", width=150)
        self.leaderboard_tree.column("TotalExpense", width=150)

        self.leaderboard_tree.heading("Rank", text="Rank")
        self.leaderboard_tree.heading("UserID", text="UserID")
        self.leaderboard_tree.heading("FirstName", text="First Name")
        self.leaderboard_tree.heading("LastName", text="Last Name")
        self.leaderboard_tree.heading("TotalExpense", text="Total Expense")

        self.leaderboard_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    def load_leaderboard_data(self, limit):
        # Clear the treeview
        for i in self.leaderboard_tree.get_children():
            self.leaderboard_tree.delete(i)

        # Fetch leaderboard data from the database
        leaderboard_data = self.database.get_expense_leaderboard_data()

        # Sort the data based on TotalSavings in descending order
        sorted_data = sorted(leaderboard_data, key=lambda x: x[-1], reverse=True)

        # Apply limit
        if limit == "top10":
            sorted_data = sorted_data[:10]
        elif limit == "top50":
            sorted_data = sorted_data[:50]
        elif limit == "top100":
            sorted_data = sorted_data[:100]
        # 'all' will show all entries

        # Insert sorted data into the treeview
        for index, item in enumerate(sorted_data, start=1):
            self.leaderboard_tree.insert('', tk.END, values=(index,) + item)

    # Placeholder methods for menu commands
    def back_to_dashboard(self):
        self.window.destroy()  # Close the savings window
        DashboardWindow(self.database, self.user_id)

    def overall_placement(self):
        self.window.destroy()
        OverallPlacementWindow(self.database, self.user_id)  # Implement the functionality

    def savings_leaderboard(self):
        self.window.destroy()
        SavingsLeaderboardWindow(self.database, self.user_id)  # Implement the functionality

    def net_worth_leaderboard(self):
        self.window.destroy()
        NetWorthLeaderboardWindow(self.database, self.user_id)


class NetWorthLeaderboardWindow:
    def __init__(self, database, user_id):
        self.database = database
        self.user_id = user_id
        self.window = tk.Tk()
        self.window.title("Net Worth Leaderboard")
        self.window.geometry("1200x1200")  # Adjust the size as needed

        self.create_widgets()
        self.load_leaderboard_data("all")
        self.window.mainloop()

    def create_widgets(self):
        # Menu bar setup
        menubar = Menu(self.window)
        self.window.config(menu=menubar)

        # Leaderboard options menu
        leaderboard_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Leaderboard Options", menu=leaderboard_menu)
        leaderboard_menu.add_command(label="Overall Placement", command=self.overall_placement)
        leaderboard_menu.add_command(label="Savings Leaderboard", command=self.savings_leaderboard)
        leaderboard_menu.add_command(label="Expenses Leaderboard", command=self.expenses_leaderboard)

        menubar.add_command(label="Back to Dashboard", command=self.back_to_dashboard)
        # Leaderboard label
        tk.Label(self.window, text="Net Worth Leaderboard", font=("Arial", 24)).pack(pady=20)

        # Buttons for leaderboard limits
        buttons_frame = tk.Frame(self.window)
        buttons_frame.pack(pady=10)
        tk.Button(buttons_frame, text="Top 10", command=lambda: self.load_leaderboard_data("top10")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Top 50", command=lambda: self.load_leaderboard_data("top50")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Top 100", command=lambda: self.load_leaderboard_data("top100")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Show All", command=lambda: self.load_leaderboard_data("all")).pack(side=tk.LEFT)
        tk.Button(buttons_frame, text="Refresh", command=lambda: self.load_leaderboard_data("all")).pack(side=tk.RIGHT)

        # Treeview for displaying leaderboard
        self.leaderboard_tree = ttk.Treeview(self.window, columns=("Rank", "UserID", "FirstName", "LastName", "NetWorth"), show='headings')
        self.leaderboard_tree.column("Rank", width=50)
        self.leaderboard_tree.column("UserID", width=100)
        self.leaderboard_tree.column("FirstName", width=150)
        self.leaderboard_tree.column("LastName", width=150)
        self.leaderboard_tree.column("NetWorth", width=150)

        self.leaderboard_tree.heading("Rank", text="Rank")
        self.leaderboard_tree.heading("UserID", text="UserID")
        self.leaderboard_tree.heading("FirstName", text="First Name")
        self.leaderboard_tree.heading("LastName", text="Last Name")
        self.leaderboard_tree.heading("NetWorth", text="Net Worth")

        self.leaderboard_tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    def load_leaderboard_data(self, limit):
        # Clear the treeview
        for i in self.leaderboard_tree.get_children():
            self.leaderboard_tree.delete(i)

        # Fetch leaderboard data from the database
        leaderboard_data = self.database.get_net_worth_leaderboard_data()

        # Sort the data based on NetWorth in descending order
        sorted_data = sorted(leaderboard_data, key=lambda x: x[-1], reverse=True)

        # Apply limit
        if limit == "top10":
            sorted_data = sorted_data[:10]
        elif limit == "top50":
            sorted_data = sorted_data[:50]
        elif limit == "top100":
            sorted_data = sorted_data[:100]
        # 'all' will show all entries

        # Insert sorted data into the treeview
        for index, item in enumerate(sorted_data, start=1):
            self.leaderboard_tree.insert('', tk.END, values=(index,) + item)

    # Placeholder methods for menu commands
    def back_to_dashboard(self):
        self.window.destroy()  # Close the savings window
        DashboardWindow(self.database, self.user_id)

    def overall_placement(self):
        self.window.destroy()
        OverallPlacementWindow(self.database, self.user_id)  # Implement the functionality

    def savings_leaderboard(self):
        self.window.destroy()
        SavingsLeaderboardWindow(self.database, self.user_id)  # Implement the functionality

    def expenses_leaderboard(self):
        self.window.destroy()
        ExpenseLeaderboardWindow(self.database, self.user_id)  # Implement the functionality

import tkinter as tk
from tkinter import ttk, Menu

class OverallPlacementWindow:
    def __init__(self, database, user_id):
        self.database = database
        self.user_id = user_id
        self.window = tk.Tk()
        self.window.title("Overall Placement")
        self.window.geometry("1200x1200")  # Adjust the size as needed

        self.create_widgets()
        self.load_user_placement()
        self.window.mainloop()

    def create_widgets(self):
        # Menu bar setup
        menubar = Menu(self.window)
        self.window.config(menu=menubar)

        # Leaderboard options menu
        leaderboard_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Leaderboard Options", menu=leaderboard_menu)
        leaderboard_menu.add_command(label="Savings Leaderboard", command=self.savings_leaderboard)
        leaderboard_menu.add_command(label="Expenses Leaderboard", command=self.expenses_leaderboard)
        leaderboard_menu.add_command(label="Net Worth Leaderboard", command=self.net_worth_leaderboard)

        menubar.add_command(label="Back to Dashboard", command=self.back_to_dashboard)
        # Placement label
        self.placement_label = tk.Label(self.window, text="", font=("Arial", 24))
        self.placement_label.pack(pady=20)

        self.placement2_label = tk.Label(self.window, text="", font=("Arial", 24))
        self.placement2_label.pack(pady=20)
        
        self.placement3_label = tk.Label(self.window, text="", font=("Arial", 24))
        self.placement3_label.pack(pady=20)


    def load_user_placement(self):
        # Fetch user's overall placement from the database
        leaderboard_data = self.database.get_net_worth_leaderboard_data()
        
        def find_user_position_in_leaderboard(leaderboard_data, user_id):
        
            for position, data in enumerate(leaderboard_data, start=1):
                if data[0] == user_id:  # Assuming the UserID is the first element in the data tuple
                    return position
            return None
        placement = find_user_position_in_leaderboard(leaderboard_data,self.user_id)
        total_users = self.database.get_total_number_of_users()

        # Update the label with the user's placement
        self.placement_label.config(text=f"Your Overall Placement: {placement}")
        self.placement2_label.config(text=f"{placement} / {total_users}")
        percentile_rank = ((total_users - placement) / (total_users - 1)) * 100
        self.placement3_label.config(text=f"Your in the Top {percentile_rank} Percentile")
        # Placeholder methods for menu commands
    def back_to_dashboard(self):
        self.window.destroy()  # Close the savings window
        DashboardWindow(self.database, self.user_id)
        
    def savings_leaderboard(self):
        self.window.destroy()
        SavingsLeaderboardWindow(self.database, self.user_id)

    def expenses_leaderboard(self):
        self.window.destroy()
        ExpenseLeaderboardWindow(self.database, self.user_id)

    def net_worth_leaderboard(self):
        self.window.destroy()
        NetWorthLeaderboardWindow(self.database, self.user_id)

if __name__ == "__main__":
    db = Database("SaveSphere", "postgres", "e8a39ccb71", "127.0.0.1")
    open_login_window()  # Open the login window directly
