import tkinter as tk
from tkinter.messagebox import askyesno
from os.path import join, dirname, abspath, exists
from datetime import datetime

###################################################
#                   CLASS ITEM                    #
###################################################
class Item:
    def __init__(self, name, price):
        self.name = name
        self.price = price

        return;

    def __str__(self):
        return f"{self.name} - €{self.price:.2f}";

###################################################
#                   CLASS TABLE                   #
###################################################
class Table:
    def __init__(self, table_id):
        self.table_id = table_id
        self.start_time = None
        self.orders = {} # Dict: { item_name: quantity }

        return;

    def add_item(self, item_name, qty=1):
        """Adds (or subtracts if qty < 0) an item."""
        if self.start_time is None and qty > 0:
            self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if item_name not in self.orders:
            self.orders[item_name] = 0
        self.orders[item_name] += qty

        # If quantity goes <= 0, remove it
        if self.orders[item_name] <= 0:
            del self.orders[item_name]
            # If no items left, reset start_time
            if not self.orders:
                self.start_time = None

        return;

    def remove_item(self, item_name, qty=1):
        self.add_item(item_name, -qty)
        return;

    def get_total(self, price_map):
        total = 0.0
        for iname, quantity in self.orders.items():
            price = price_map.get(iname, 0.0)
            total += price * quantity

        return total;

    def complete_order(self):
        self.orders.clear()
        self.start_time = None

        return;

###################################################
#                LOAD MENU/TXT                    #
###################################################
def load_menu(menu_file="menu.txt"):
    """
    Returns (flat_items, menu_dict).
      flat_items: [Item, Item, ...]
      menu_dict: { "ΟΡΕΚΤΙΚΑ": [...], "ΣΑΛΑΤΕΣ": [...], ... }
    """
    if not exists(menu_file):
        print(f"[!] Menu file not found: {menu_file}")
        return [], {};

    with open(menu_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]

    flat_items = []
    menu_dict = {}
    current_category = None

    for line in lines:
        if not line:
            continue;
        if "-" not in line:
            current_category = line
            menu_dict[current_category] = []
        else:
            try:
                parts = line.split("-")
                iname = parts[0].strip()
                iprice = float(parts[1].strip())
                item_obj = Item(iname, iprice)
                flat_items.append(item_obj)
                if current_category:
                    menu_dict[current_category].append(item_obj)
            except Exception as e:
                print(f"Error parsing '{line}': {e}")

    return flat_items, menu_dict;

###################################################
#            LOAD SETTINGS (tables)               #
###################################################
def load_settings(settings_file="settings.txt"):
    settings = {}
    if not exists(settings_file):
        settings["ARITHMOS_TRAPEZION"] = "12"
        return settings;

    with open(settings_file, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if "=" in line:
                key, val = line.split("=", 1)
                settings[key.strip()] = val.strip()

    return settings;

###################################################
#         SAVE/LOAD ORDERS (simple text)          #
###################################################
def save_orders(tables_list, orders_file="orders.txt"):
    """
    Write lines: table_id|item_name|quantity|start_time
    """
    try:
        with open(orders_file, "w", encoding="utf-8") as f:
            for table in tables_list:
                if table.start_time and len(table.orders)>0:
                    for iname, qty in table.orders.items():
                        line = f"{table.table_id}|{iname}|{qty}|{table.start_time}"
                        f.write(line + "\n")
    except Exception as e:
        print(f"[!] Error saving orders: {e}")

    return;

def load_orders(tables_list, orders_file="orders.txt"):
    if not exists(orders_file):
        return;

    for t in tables_list:
        t.orders.clear()
        t.start_time = None

    try:
        with open(orders_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f]
        for line in lines:
            parts = line.split("|")
            if len(parts)!=4:
                continue;
            tid_str, iname, qty_str, stime = parts
            try:
                tid = int(tid_str)
                qty = int(qty_str)
            except:
                continue;
            # find table
            the_table = None
            for tbl in tables_list:
                if tbl.table_id == tid:
                    the_table = tbl
                    break;
            if the_table:
                the_table.orders[iname] = qty
                if not the_table.start_time:
                    the_table.start_time = stime
    except Exception as e:
        print(f"[!] Error loading orders: {e}")

    return;

###################################################
#              TKINTER GUI MANAGER                #
###################################################
class TableManagerGUI:
    def __init__(self, root, tables, items, menu_dict):
        self.root = root
        self.root.title("ΚΑΠΟΥ... ΚΑΠΟΥ... ΤΣΙΠΟΥΡΑΔΙΚΟ")
        self.root.state("zoomed")

        self.tables = tables
        self.selected_table = None # Which table is currently "selected"

        # Price map for quick lookups
        self.price_map = {}
        for it in items:
            self.price_map[it.name] = it.price

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill="both", expand=True)

        # Left part: Scrollable area for Tables
        left_frame = tk.Frame(main_frame, bg="white")
        left_frame.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(left_frame, bg="white")
        self.canvas.pack(side="left", fill="both", expand=True)

        scroll_y = tk.Scrollbar(left_frame, orient="vertical", command=self.canvas.yview)
        scroll_y.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=scroll_y.set)
        # The actual container
        self.tables_container = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0,0), window=self.tables_container, anchor="nw")

        # Update scroll region
        self.tables_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Build the TABLES in a grid of 4 columns
        self.build_tables_grid()

        # Right part: The Menu
        self.right_frame = tk.Frame(main_frame, bd=2, relief="sunken", bg="white", width=300)
        self.right_frame.pack(side="right", fill="both", expand=False)

        self.lbl_menu = tk.Label(self.right_frame, text="ΚΑΤΑΛΟΓΟΣ", font=("Arial",14,"bold"), bg="white")
        self.lbl_menu.pack(pady=10)

        # Add the "Unselect" button below the "MENU" label
        self.btn_unselect = tk.Button(self.right_frame, text="Αποεπιλογή τραπεζιού", command=self.unselect_table)
        self.btn_unselect.pack(pady=5)


        # Create a Canvas for the menu with a vertical scrollbar
        self.menu_canvas = tk.Canvas(self.right_frame, bg="white")
        self.menu_canvas.pack(side="left", fill="both", expand=True)

        self.menu_scrollbar = tk.Scrollbar(self.right_frame, orient="vertical", command=self.menu_canvas.yview)
        self.menu_scrollbar.pack(side="right", fill="y")

        self.menu_canvas.configure(yscrollcommand=self.menu_scrollbar.set)

        # The frame inside the canvas
        self.menu_inner_frame = tk.Frame(self.menu_canvas, bg="white")
        self.menu_canvas.create_window((0,0), window=self.menu_inner_frame, anchor="nw")

        # Update scroll region when the inner frame changes
        self.menu_inner_frame.bind(
            "<Configure>",
            lambda e: self.menu_canvas.configure(scrollregion=self.menu_canvas.bbox("all"))
        )

        # Store menu_dict for building categorized menu
        self.menu_dict = menu_dict

        # Bind mouse wheel events to the menu canvas
        self.bind_mouse_wheel(self.menu_canvas)

        # Build the categorized, scrollable menu items
        self.build_menu_items()

        # Start the auto-save timer
        self.start_auto_save()

        # On close => save
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        return;

    ###################################################
    #       BUILD TABLES ON LEFT (GRID of 4 col)      #
    ###################################################
    def build_tables_grid(self):
        colors = ["tomato","lightskyblue","palegreen","pink","orange",
                  "khaki","salmon","plum","lightblue","palegreen",
                  "gold","thistle","lightgray","lemonchiffon"]

        columns_per_row = 4

        for idx, table in enumerate(self.tables):
            c = colors[idx % len(colors)] # color

            row_i = idx // columns_per_row
            col_i = idx % columns_per_row

            # The outer frame
            tbl_frame = tk.Frame(self.tables_container,
                                 bg=c,
                                 bd=3,
                                 relief="ridge",
                                 width=200,
                                 height=140)
            tbl_frame.grid(row=row_i, column=col_i, padx=10, pady=10)

            table.__dict__["ui_frame"] = tbl_frame

            # We will refresh the inside
            self.refresh_table_ui(table)

        return;

    def refresh_table_ui(self, table):
        """Clear & rebuild the inside of each table frame."""
        frame = table.__dict__["ui_frame"]
        bg_color = frame["bg"]

        for w in frame.winfo_children():
            w.destroy() # Clear old

        # Label "Table X"
        lbl_title = tk.Label(frame, text=f"Τραπέζι {table.table_id}", font=("Arial",10,"bold"), bg=bg_color)
        lbl_title.pack(anchor="nw", padx=5, pady=2)

        # Click => select table
        frame.bind("<Button-1>", lambda e, t=table: self.select_table(t))
        lbl_title.bind("<Button-1>", lambda e, t=table: self.select_table(t))

        # Έναρξη:
        lbl_start = tk.Label(frame,
                             text=f"Έναρξη: {table.start_time if table.start_time else '-'}",
                             font=("Arial",8,"italic"),
                             bg=bg_color)
        lbl_start.pack(anchor="nw", padx=5)

        # Show the items (read-only)
        # We'll just do multiline labels or small lines
        if table.orders:
            for iname, qty in table.orders.items():
                lbl_item = tk.Label(frame,
                                    text=f"{iname}: {qty}",
                                    font=("Arial",9),
                                    bg=bg_color)
                lbl_item.pack(anchor="nw", padx=5)
        else:
            # maybe a label "No items"
            pass;

        # Show total
        total_val = table.get_total(self.price_map)
        lbl_total = tk.Label(frame, text=f"Σύνολο: €{total_val:.2f}", font=("Arial",9,"bold"), bg=bg_color)
        lbl_total.pack(anchor="nw", padx=5, pady=5)

        # Complete Order
        btn_complete = tk.Button(frame, text="Ολοκλήρωση Παραγγελίας", command=lambda: self.complete_order(table))
        btn_complete.pack(anchor="se", padx=5, pady=5)

        # Highlight if selected
        if table == self.selected_table:
            frame.config(relief="solid", bd=5)
        else:
            frame.config(relief="ridge", bd=3)

        return;

    def select_table(self, table):
        self.selected_table = table
        # refresh all so we see highlight
        for t in self.tables:
            self.refresh_table_ui(t)

        # Update menu background color
        selected_color = table.__dict__["ui_frame"]["bg"]
        self.update_menu_color(selected_color)

        return;

    def unselect_table(self):
        if self.selected_table is not None:
            self.selected_table = None
            # Refresh all tables to remove highlighting
            for t in self.tables:
                self.refresh_table_ui(t)
            self.update_menu_color("white") # Reset menu background color to default

        return;

    def update_menu_color(self, color):
        """
        Update the background color of the menu to match the selected table's color.
        Also update all child widgets to maintain consistency.
        """
        self.right_frame.config(bg=color)
        self.lbl_menu.config(bg=color)

        # Update menu_canvas and menu_inner_frame background
        self.menu_canvas.config(bg=color)
        self.menu_inner_frame.config(bg=color)

        # Recursively update background of all child widgets in menu_inner_frame
        self.update_widget_bg(self.menu_inner_frame, color)

        return;

    def update_widget_bg(self, widget, color):
        """
        Recursively update the background color of the given widget and its children.
        """
        try:
            widget.config(bg=color)
        except:
            pass;  # Some widgets might not support bg change

        for child in widget.winfo_children():
            self.update_widget_bg(child, color)

        return;

    def complete_order(self, table):
        if not askyesno("Ερώτηση", "Είσαι σίγουρος/η;"):
            return;

        if table.orders:
            self.save_completed_order(table)
        table.complete_order()
        self.refresh_table_ui(table)
        # If needed, also update the menu's background if no table is selected
        if not table.orders:
            self.update_menu_color("white")  # Default color
        self.unselect_table()

        return;

    ###################################################
    #         BUILD MENU ON THE RIGHT SIDE            #
    ###################################################
    def build_menu_items(self):
        """
        Build the menu with category titles and items under each category.
        The menu is scrollable.
        """
        for widget in self.menu_inner_frame.winfo_children():
            widget.destroy()

        for category, items in self.menu_dict.items():
            # Category Title
            lbl_category = tk.Label(self.menu_inner_frame, text=category, font=("Arial",12,"bold"), anchor="w", bg=self.menu_inner_frame["bg"])
            lbl_category.pack(fill="x", padx=5, pady=(10, 2))

            # Items under the category
            for item in items:
                item_frame = tk.Frame(self.menu_inner_frame, bg=self.menu_inner_frame["bg"])
                item_frame.pack(fill="x", padx=10, pady=2)

                # minus button
                btn_minus = tk.Button(item_frame, text="–", width=3, command=lambda i=item.name: self.menu_remove_item(i))
                btn_minus.pack(side="left")

                # name label
                lbl_name = tk.Label(item_frame, text=item.name, font=("Arial",9), anchor="w", bg=self.menu_inner_frame["bg"])
                lbl_name.pack(side="left", padx=(5, 0))

                # spacer
                spacer = tk.Label(item_frame, text="", bg=self.menu_inner_frame["bg"])
                spacer.pack(side="left", expand=True)

                # price label
                lbl_price = tk.Label(item_frame, text=f"{item.price:.2f} €", font=("Arial",9), anchor="e", bg=self.menu_inner_frame["bg"])
                lbl_price.pack(side="left", padx=(0,5))

                # plus button
                btn_plus = tk.Button(item_frame, text="+", width=3, command=lambda i=item.name: self.menu_add_item(i))
                btn_plus.pack(side="left")

        return;

    def menu_add_item(self, iname):
        if not self.selected_table:
            return;

        self.selected_table.add_item(iname, 1)
        self.refresh_table_ui(self.selected_table)

        # Print to terminal
        price = self.price_map.get(iname, 0.0)
        print(f"Τραπέζι {self.selected_table.table_id} => +1 {iname} {price:.2f}€") # Don't forget the menu_remove_item string!

        return;

    def menu_remove_item(self, iname):
        if not self.selected_table:
            return;
        if iname not in self.selected_table.orders:
            return;

        self.selected_table.remove_item(iname, 1)
        self.refresh_table_ui(self.selected_table)

        # Print to terminal
        price = self.price_map.get(iname, 0.0)
        print(f"Τραπέζι {self.selected_table.table_id} => -1 {iname} {price:.2f}€")

        return;

    ###################################################
    #                   TIMER METHODS                 #
    ###################################################
    def start_auto_save(self):
        """Start the auto-save timer to save orders every 4 minutes."""
        self.save_orders_timer()
        return;

    def save_orders_timer(self):
        """Save orders and reschedule the timer."""
        save_orders(self.tables, "orders.txt")
        self.root.after(120000, self.save_orders_timer) # Schedule the next save

        return;

    ###################################################
    #              MOUSE WHEEL SCROLLING              #
    ###################################################
    def bind_mouse_wheel(self, widget):
        """
        Bind mouse wheel events to the given widget for scrolling.
        Handles different operating systems.
        """
        widget.bind("<Enter>", lambda e: self.bind_to_mousewheel(widget))
        widget.bind("<Leave>", lambda e: self.unbind_from_mousewheel(widget))

        return;

    def bind_to_mousewheel(self, widget):
        widget.bind_all("<MouseWheel>", lambda event: self.on_mousewheel(event, widget))
        return;

    def unbind_from_mousewheel(self, widget):
        widget.unbind_all("<MouseWheel>")
        return;

    def on_mousewheel(self, event, widget):
        """
        Handle mouse wheel scrolling.
        """
        widget.yview_scroll(int(-1*(event.delta/120)), "units")
        return;

    ###################################################
    #        SAVE COMPLETED ORDERS TO FILE            #
    ###################################################
    def save_completed_order(self, table):
        """
        Save the completed order to 'completed_orders.txt' with all details.
        """
        try:
            with open("completed_orders.txt", "a", encoding="utf-8") as f:
                f.write(f"Τραπέζι {table.table_id}\n")
                f.write(f"Έναρξη: {table.start_time}\n")
                f.write("Παραγγελίες:\n")
                for iname, qty in table.orders.items():
                    price = self.price_map.get(iname, 0.0)
                    f.write(f" - {iname}: {qty} x {price:.2f}€ = {qty * price:.2f}€\n")
                total = table.get_total(self.price_map)
                f.write(f"Σύνολο: €{total:.2f}\n")
                f.write(f"Ολοκλήρωση: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 40 + "\n")
        except Exception as e:
            print(f"[!] Error saving completed order: {e}")
        
        return;

    ###################################################
    #                   ON CLOSE                      #
    ###################################################
    def on_close(self):
        save_orders(self.tables, "orders.txt")
        if askyesno("Έξοδος", "Είστε σίγουρος/η ότι θέλετε να κλείσετε την εφαρμογή;"):
            exit();

        return;

###################################################
#                     main()                      #
###################################################
def main():
    script_dir =    dirname(abspath(__file__))
    settings_file = join(script_dir, "settings.txt")
    menu_file =     join(script_dir, "menu.txt")
    orders_file =   join(script_dir, "orders.txt")

    settings = load_settings(settings_file)
    num_tables = int(settings.get("ARITHMOS_TRAPEZION", 12))
    tables = [Table(i) for i in range(1, num_tables + 1)] # Create tables

    flat_items, menu_dict = load_menu(menu_file) # Load menu

    load_orders(tables, orders_file) # Load existing orders
    
    root = tk.Tk()
    app = TableManagerGUI(root, tables, flat_items, menu_dict)
    root.mainloop()

    return;

if __name__ == "__main__":
    main()
