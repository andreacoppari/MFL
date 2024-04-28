import tkinter as tk
import webbrowser

def open_url_in_browser(url):
    webbrowser.open(url)

root = tk.Tk()
root.title("MFL - My Favourite Links")
root.geometry("600x400")

bg_color = "#f0f0f0"
button_bg = "#4caf50"
button_fg = "white"
button_font = ("Helvetica", 12, "bold")

button_frame = tk.Frame(root, bg=bg_color)
button_frame.pack(pady=20, padx=10, fill=tk.BOTH, expand=True)

urls = {
    "WordReference": "https://www.wordreference.com/iten/",
    "Deepl": "https://www.deepl.com/en/translator",
    "The Free Dictionary": "https://www.thefreedictionary.com/",
    "Sketch Engine": "https://app.sketchengine.eu/#dashboard?corpname=preloaded%2Fententen21_tt31",
    "Treccani": "https://www.treccani.it/"
}

def open_all_urls():
    for site_url in urls.values():
        open_url_in_browser(site_url)

for site_name, site_url in urls.items():
    button = tk.Button(button_frame, text=site_name, bg=button_bg, fg=button_fg, font=button_font, bd=2, relief=tk.RAISED,
                       padx=20, pady=10, width=20, command=lambda url=site_url: open_url_in_browser(url))
    button.pack(pady=10, fill=tk.X)

open_all_button = tk.Button(root, text="Open All Websites", bg=button_bg, fg=button_fg, font=button_font,
                            bd=2, relief=tk.RAISED, padx=20, pady=10, width=20, command=open_all_urls)
open_all_button.pack(pady=20)

root.mainloop()
