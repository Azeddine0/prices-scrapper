import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

class PriceScraperBot:
    def __init__(self, log_callback):
        self.sites = []
        self.interval = 60
        self.running = False
        self.thread = None
        self.log_callback = log_callback
        self.data = []

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def set_sites(self, sites):
        self.sites = sites

    def set_interval(self, minutes):
        self.interval = minutes

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_bot, daemon=True)
            self.thread.start()
            self.log("Bot started.")

    def stop(self):
        if self.running:
            self.running = False
            self.log("Stopping bot...")

    def get_price_from_url(self, url, selector=None):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                 '(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        if selector:
            price_tag = soup.select_one(selector)
            if price_tag:
                return price_tag.get_text(strip=True)
            else:
                raise ValueError(f"Price element not found with selector '{selector}'")
        else:
            common_selectors = ['.price', '#price', '[class*="price"]', '[id*="price"]']
            for sel in common_selectors:
                price_tag = soup.select_one(sel)
                if price_tag:
                    return price_tag.get_text(strip=True)
            raise ValueError("Price element not found with default selectors")

    def scrape_all_sites(self):
        self.data = []
        for url, selector in self.sites:
            if not self.running:
                break
            self.log(f"Scraping {url} ...")
            try:
                price = self.get_price_from_url(url, selector)
                self.log(f"Price found: {price}")
                self.data.append({"url": url, "price": price, "timestamp": datetime.now()})
            except Exception as e:
                self.log(f"Error scraping {url}: {e}")

    def save_data(self, filename="scraped_prices.csv"):
        df = pd.DataFrame(self.data)
        try:
            df_existing = pd.read_csv(filename)
            df = pd.concat([df_existing, df], ignore_index=True)
        except FileNotFoundError:
            pass
        df.to_csv(filename, index=False)
        self.log(f"Data saved to {filename}")

    def run_bot(self):
        while self.running:
            self.log("Starting scraping round...")
            self.scrape_all_sites()
            if self.data:
                self.save_data()
            else:
                self.log("No data scraped this round.")
            self.log(f"Sleeping for {self.interval} minutes...\n")
            for _ in range(self.interval * 6):
                if not self.running:
                    break
                time.sleep(10)
        self.log("Bot stopped.")


class PriceScraperUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Price Scraper Bot")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Input frame
        input_frame = ttk.LabelFrame(root, text="URLs and CSS Selectors")
        input_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)

        instructions = ("Enter URLs and optional CSS selectors (one per line):\n"
                        "Format: URL [space] CSS_SELECTOR\n"
                        "Example:\n"
                        "https://example.com/product .price\n"
                        "Leave selector empty to try default selectors.")
        self.instructions_label = ttk.Label(input_frame, text=instructions, justify=tk.LEFT)
        self.instructions_label.pack(fill=tk.X, padx=5, pady=5)

        self.url_text = ScrolledText(input_frame, height=12)
        self.url_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Interval frame
        interval_frame = ttk.Frame(root)
        interval_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(interval_frame, text="Scrape interval (minutes):").pack(side=tk.LEFT, padx=(0,5))
        self.interval_var = tk.StringVar(value="60")
        self.interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=8)
        self.interval_entry.pack(side=tk.LEFT)

        # Buttons frame
        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        self.start_button = ttk.Button(btn_frame, text="Start Bot", command=self.start_bot)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(btn_frame, text="Stop Bot", command=self.stop_bot, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = ttk.Button(btn_frame, text="Clear Logs", command=self.clear_logs)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # Log frame
        log_frame = ttk.LabelFrame(root, text="Log Output")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.output_text = ScrolledText(log_frame, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.bot = PriceScraperBot(log_callback=self.log_message)

        # Responsive resizing
        root.columnconfigure(0, weight=1)
        root.rowconfigure(3, weight=1)

    def log_message(self, message):
        def append():
            self.output_text.configure(state=tk.NORMAL)
            self.output_text.insert(tk.END, message + "\n")
            self.output_text.see(tk.END)
            self.output_text.configure(state=tk.DISABLED)
        self.root.after(0, append)

    def start_bot(self):
        urls_input = self.url_text.get("1.0", tk.END).strip()
        if not urls_input:
            messagebox.showwarning("Input needed", "Please enter at least one URL.")
            return

        try:
            interval = int(self.interval_var.get())
            if interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid interval", "Please enter a positive integer for interval.")
            return

        sites = []
        for line in urls_input.splitlines():
            if not line.strip():
                continue
            parts = line.split(maxsplit=1)
            url = parts[0]
            selector = parts[1] if len(parts) > 1 else None
            sites.append((url, selector))

        self.bot.set_sites(sites)
        self.bot.set_interval(interval)
        self.bot.start()

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

    def stop_bot(self):
        self.bot.stop()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def clear_logs(self):
        self.output_text.configure(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.configure(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = PriceScraperUI(root)
    root.mainloop()