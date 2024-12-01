import customtkinter as ctk 
from tkcalendar import Calendar
from datetime import datetime, timedelta
import threading
import time
import json
from CTkMessagebox import CTkMessagebox
import ctypes
from typing import List
from queue import Queue
import uuid


try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

class Theme:
    PRIMARY = "#1f538d" #dark blue
    SECONDARY = "#14375e" #blue
    SUCCESS = "#2fa572" # dark cyan
    WARNING = "#e69138" # bright orange
    DANGER = "#cc0000" #gaurdsman red
    
    @staticmethod
    def set_theme():
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

class ReminderState:
    def __init__(self, event_id: str, notification_time: datetime):
        self.event_id = event_id
        self.notification_time = notification_time
        self.notified = False
        
    def should_notify(self, current_time: datetime) -> bool:
        return (not self.notified and 
                self.notification_time <= current_time < 
                self.notification_time + timedelta(minutes=1))
    
    def mark_notified(self):
        self.notified = True

class EventData:
    def __init__(self, text: str, datetime_obj: datetime, reminder_minutes: int, 
                 category: str = "General", event_id: str = None):
        self.text = text
        self.datetime = datetime_obj
        self.reminder_minutes = reminder_minutes
        self.category = category
        self.event_id = event_id or str(uuid.uuid4())
        self.reminder_state = None
        self.update_reminder_state()
    
    def update_reminder_state(self):
        if self.reminder_minutes > 0:
            notification_time = self.datetime - timedelta(minutes=self.reminder_minutes)
            self.reminder_state = ReminderState(self.event_id, notification_time)
        else:
            self.reminder_state = None
        
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "datetime": self.datetime.strftime("%Y-%m-%d %H:%M"),
            "reminder_minutes": self.reminder_minutes,
            "category": self.category,
            "event_id": self.event_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EventData':
        event = cls(
            text=data["text"],
            datetime_obj=datetime.strptime(data["datetime"], "%Y-%m-%d %H:%M"),
            reminder_minutes=data["reminder_minutes"],
            category=data.get("category", "General"),
            event_id=data.get("event_id")
        )
        event.update_reminder_state()
        return event

class ReminderManager:
    def __init__(self):
        self.reminder_queue = Queue()
        self.active_reminders = {}
        self.last_check = datetime.now()
    
    def add_reminder(self, event: EventData):
        if event.reminder_state:
            self.active_reminders[event.event_id] = event
    
    def remove_reminder(self, event_id: str):
        self.active_reminders.pop(event_id, None)
    
    def check_reminders(self, current_time: datetime) -> List[EventData]:
        due_reminders = []
        for event in list(self.active_reminders.values()):
            if event.reminder_state and event.reminder_state.should_notify(current_time):
                due_reminders.append(event)
                event.reminder_state.mark_notified()
                if current_time > event.datetime:
                    self.remove_reminder(event.event_id)
        return due_reminders

class AdvancedCalendarApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.setup_window()
        self.events = {}
        self.reminder_manager = ReminderManager()
        self.reminder_interval = 1  # Check every second
        self.categories = ["General", "Work", "Personal", "Important"]
        self.load_events()
        self.create_widgets()
        self.start_reminder_thread()

    def setup_window(self):
        self.root.title("Advanced Calendar")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 1000
        window_height = 700
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        Theme.set_theme()

    def create_widgets(self):
        self.content_frame = ctk.CTkFrame(self.root)
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.left_panel = ctk.CTkFrame(self.content_frame)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=10)

        self.cal = Calendar(
            self.left_panel,
            selectmode="day",
            date_pattern="yyyy-mm-dd",
            font=("Arial", 12),
            background=Theme.PRIMARY,
            foreground="white",
            selectbackground=Theme.SECONDARY
        )
        self.cal.pack(pady=20, padx=20, fill="both", expand=True)

        self.right_panel = ctk.CTkFrame(self.content_frame)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=10)

        self.events_frame = ctk.CTkFrame(self.right_panel)
        self.events_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.events_label = ctk.CTkLabel(
            self.events_frame,
            text="Today's Events",
            font=("Arial", 16, "bold")
        )
        self.events_label.pack(pady=10)

        self.events_text = ctk.CTkTextbox(
            self.events_frame,
            wrap="word",
            height=200
        )
        self.events_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.buttons_frame = ctk.CTkFrame(self.right_panel)
        self.buttons_frame.pack(fill="x", pady=10)

        self.add_button = ctk.CTkButton(
            self.buttons_frame,
            text="Add Event",
            command=self.add_event,
            fg_color=Theme.SUCCESS
        )
        self.add_button.pack(side="left", padx=5, expand=True)

        self.delete_button = ctk.CTkButton(
            self.buttons_frame,
            text="Delete Event",
            command=self.delete_event,
            fg_color=Theme.DANGER
        )
        self.delete_button.pack(side="left", padx=5, expand=True)

        self.cal.bind("<<CalendarSelected>>", self.update_events_display)
        
        self.update_events_display()

    def update_events_display(self, event=None):
        selected_date = self.cal.get_date()
        events = self.events.get(selected_date, [])
        
        self.events_text.delete("1.0", "end")
        if events:
            for event in sorted(events, key=lambda x: x.datetime):
                time_str = event.datetime.strftime("%H:%M")
                self.events_text.insert("end", f"⏰ {time_str}\n")
                self.events_text.insert("end", f"📝 {event.text}\n")
                self.events_text.insert("end", f"🏷️ Category: {event.category}\n")
                self.events_text.insert("end", f"⏲️ Reminder: {event.reminder_minutes} minutes before\n")
                self.events_text.insert("end", "─" * 40 + "\n\n")
        else:
            self.events_text.insert("end", "No events scheduled for this date.")

    def save_events(self):
        events_dict = {}
        for date, events_list in self.events.items():
            events_dict[date] = [event.to_dict() for event in events_list]
            
        with open("calendar_events.json", "w") as f:
            json.dump(events_dict, f)

    def add_event(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Add Event")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Event Details", font=("Arial", 16, "bold")).pack(pady=10)
        
        ctk.CTkLabel(dialog, text="Event Description:").pack(pady=(10, 0))
        event_text = ctk.CTkEntry(dialog, width=300)
        event_text.pack(pady=(0, 10))

        ctk.CTkLabel(dialog, text="Event Time (HH:MM):").pack(pady=(10, 0))
        time_entry = ctk.CTkEntry(dialog, width=300)
        time_entry.insert(0, datetime.now().strftime("%H:%M"))
        time_entry.pack(pady=(0, 10))

        ctk.CTkLabel(dialog, text="Reminder (minutes before):").pack(pady=(10, 0))
        reminder_entry = ctk.CTkEntry(dialog, width=300)
        reminder_entry.insert(0, "30")
        reminder_entry.pack(pady=(0, 10))

        ctk.CTkLabel(dialog, text="Category:").pack(pady=(10, 0))
        category_var = ctk.StringVar(value=self.categories[0])
        category_dropdown = ctk.CTkOptionMenu(
            dialog,
            values=self.categories,
            variable=category_var,
            width=300
        )
        category_dropdown.pack(pady=(0, 10))

        def save_event():
            try:
                selected_date = self.cal.get_date()
                event_time = time_entry.get()
                event_datetime = datetime.strptime(f"{selected_date} {event_time}", "%Y-%m-%d %H:%M")
                reminder_minutes = int(reminder_entry.get())
                
                if event_datetime < datetime.now():
                    raise ValueError("Event time must be in the future")
                
                event = EventData(
                    text=event_text.get(),
                    datetime_obj=event_datetime,
                    reminder_minutes=reminder_minutes,
                    category=category_var.get()
                )

                if selected_date not in self.events:
                    self.events[selected_date] = []
                
                self.events[selected_date].append(event)
                
                self.reminder_manager.add_reminder(event)
                
                self.save_events()
                self.update_events_display()
                dialog.destroy()
                
                CTkMessagebox(
                    title="Success",
                    message="Event added successfully!",
                    icon="check",
                    option_1="Ok"
                )
                
            except ValueError as e:
                CTkMessagebox(
                    title="Error",
                    message=str(e),
                    icon="cancel",
                    option_1="Ok"
                )

        ctk.CTkButton(
            dialog,
            text="Save Event",
            command=save_event,
            fg_color=Theme.SUCCESS
        ).pack(pady=20)

    def delete_event(self):
        selected_date = self.cal.get_date()
        events = self.events.get(selected_date, [])
        
        if not events:
            CTkMessagebox(
                title="No Events",
                message="No events to delete on this date.",
                icon="info",
                option_1="Ok"
            )
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Delete Event")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Select event to delete:", font=("Arial", 14)).pack(pady=10)

        selected_event = ctk.StringVar()
        for i, event in enumerate(events):
            event_text = f"{event.datetime.strftime('%H:%M')} - {event.text}"
            radio = ctk.CTkRadioButton(
                dialog,
                text=event_text,
                variable=selected_event,
                value=str(i)
            )
            radio.pack(pady=5, padx=20, anchor="w")

        def confirm_delete():
            try:
                index = int(selected_event.get())
                event = self.events[selected_date][index]
                # Remove from reminder manager
                self.reminder_manager.remove_reminder(event.event_id)

                del self.events[selected_date][index]
                if not self.events[selected_date]:
                    del self.events[selected_date]
                self.save_events()
                self.update_events_display()
                dialog.destroy()
                
                CTkMessagebox(
                    title="Success",
                    message="Event deleted successfully!",
                    icon="check",
                    option_1="Ok"
                )
            except:
                CTkMessagebox(
                    title="Error",
                    message="Please select an event to delete.",
                    icon="cancel",
                    option_1="Ok"
                )

        ctk.CTkButton(
            dialog,
            text="Delete Selected Event",
            command=confirm_delete,
            fg_color=Theme.DANGER
        ).pack(pady=20)

    def load_events(self):
        try:
            with open("calendar_events.json", "r") as f:
                events_dict = json.load(f)
                
            for date, events_list in events_dict.items():
                self.events[date] = []
                for event_data in events_list:
                    event = EventData.from_dict(event_data)
                    self.events[date].append(event)
                    
                    self.reminder_manager.add_reminder(event)
        except FileNotFoundError:
            pass

    def start_reminder_thread(self):
        def reminder_loop():
            while True:
                self.check_reminders()
                time.sleep(self.reminder_interval)
        
        threading.Thread(target=reminder_loop, daemon=True).start()

    def check_reminders(self):
        current_time = datetime.now()
        due_reminders = self.reminder_manager.check_reminders(current_time)
        
        for event in due_reminders:
        
            self.root.after(0, self.show_reminder, event)

    def show_reminder(self, event: EventData):
        
        reminder_text = (
            f"🔔 Event Reminder\n\n"
            f"Event: {event.text}\n"
            f"Time: {event.datetime.strftime('%H:%M')}\n"
            f"Category:{event.category}"
        )
        
        CTkMessagebox(
            title="Event Reminder",
            message=reminder_text,
            icon="info",
            option_1="Ok"
        )

    def run(self):
        
        self.root.mainloop()

if __name__ == "__main__":
    app = AdvancedCalendarApp()
    app.run() 
