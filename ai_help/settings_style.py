"""Small, scoped Tk styles for the companion's settings window."""
import math
import tkinter as tk
from tkinter import ttk

BG = '#FAF7FD'
INK = '#514263'
MUTED = '#93849F'
PURPLE = '#9270CE'
FONT = ('Microsoft YaHei UI', 10)


def rounded_image(master, fill, outline, radius=12):
    size = radius * 2 + 4
    image = tk.PhotoImage(master=master, width=size, height=size)
    for y in range(size):
        dy = max(radius - y, y - (size - radius - 1), 0)
        inset = math.ceil(radius - math.sqrt(max(0, radius * radius - dy * dy)))
        image.put(outline, to=(inset, y, size - inset, y + 1))
        if y not in (0, size - 1):
            image.put(fill, to=(inset + 1, y, size - inset - 1, y + 1))
    return image


def setup_styles(window):
    style = ttk.Style(window)
    # Keep image references on the Tcl interpreter's root, including across reopenings.
    root = window._root()
    if not hasattr(root, '_settings_images'):
        root._settings_images = []
    for name, fill, active, edge in (
            ('Primary', PURPLE, '#8060BB', PURPLE),
            ('Soft', '#F1EAFB', '#E7DCF7', '#F1EAFB')):
        element = 'Companion.' + name + '.border'
        if element not in style.element_names():
            radius = 12 if name == 'Primary' else 8
            normal = rounded_image(window, fill, edge, radius)
            hover = rounded_image(window, active, active, radius)
            focus = rounded_image(window, active, '#65508B', radius)
            root._settings_images.extend((normal, hover, focus))
            style.element_create(element, 'image', normal, ('pressed', hover),
                                 ('focus', focus), ('active', hover), border=radius, sticky='nswe')
        button_style = 'Companion.' + name + '.TButton'
        style.layout(button_style, [(element, {'sticky': 'nswe', 'children': [
            ('Button.padding', {'sticky': 'nswe', 'children': [
                ('Button.label', {'sticky': 'nswe'})]})]})])
        style.configure(button_style, font=FONT, padding=(16, 0), borderwidth=0,
                        foreground='white' if name == 'Primary' else '#7959A6',
                        background=BG, anchor='center')

    for kind in ('Entry', 'Combobox'):
        element = 'Companion.' + kind + '.field'
        if element not in style.element_names():
            normal = rounded_image(window, '#FCFAFF', '#E8E0F0', 8)
            focus = rounded_image(window, '#FFFFFF', '#AD8CDD', 8)
            disabled = rounded_image(window, '#F3F0F6', '#EBE6F0', 8)
            root._settings_images.extend((normal, focus, disabled))
            style.element_create(element, 'image', normal, ('disabled', disabled),
                                 ('focus', focus), border=6, sticky='nswe')
        children = [(kind + '.padding', {'sticky': 'nswe', 'children': [
            (kind + '.textarea', {'sticky': 'nswe'})]})]
        if kind == 'Combobox':
            arrow = 'Companion.Combobox.downarrow'
            if arrow not in style.element_names():
                style.element_create(arrow, 'from', 'clam', 'Combobox.downarrow')
            children.insert(0, (arrow, {'side': 'right', 'sticky': 'ns'}))
        name = 'Companion.T' + kind
        style.layout(name, [(element, {'sticky': 'nswe', 'children': children})])
        style.configure(name, font=FONT, padding=(8, 1), foreground=INK,
                        fieldbackground='#FCFAFF', background='#FCFAFF',
                        arrowcolor='#9D82BE', arrowsize=14, borderwidth=0)
        style.map(name, fieldbackground=[('disabled', '#F3F0F6'), ('readonly', '#FCFAFF')],
                  foreground=[('disabled', '#B1A7BC')],
                  selectbackground=[('!disabled', '#E8DDF7')],
                  selectforeground=[('!disabled', INK)])
    style.configure('Companion.TCheckbutton', font=FONT, background='white', foreground=INK,
                    padding=0)
    style.map('Companion.TCheckbutton', background=[('active', 'white')])


class SettingsCard(tk.Canvas):
    def __init__(self, parent, title):
        super().__init__(parent, bg=BG, highlightthickness=0, height=100)
        self.body = tk.Frame(self, bg='white')
        self.body.columnconfigure(1, weight=1)
        tk.Label(self.body, text=title, bg='white', fg='#A28AB6',
                 font=('Microsoft YaHei UI', 10, 'bold')).grid(
                     row=0, column=0, columnspan=3, sticky='w', pady=(0, 10))
        self.content = self.create_window(22, 18, anchor='nw', window=self.body)
        self.bind('<Configure>', self.resize)
        self.body.bind('<Configure>', self.fit)

    def fit(self, event=None):
        self.configure(height=self.body.winfo_reqheight() + 38)

    def resize(self, event):
        w, h, r = event.width, event.height, 22
        self.delete('card')
        points = [r, 1, w-r, 1, w-1, 1, w-1, r, w-1, h-r,
                  w-1, h-1, w-r, h-1, r, h-1, 1, h-1, 1, h-r, 1, r, 1, 1]
        self.create_polygon(points, smooth=True, splinesteps=24, fill='white',
                            outline='#EEE6F5', tags='card')
        self.tag_lower('card')
        self.itemconfigure(self.content, width=max(1, w - 44))


def draw_cat(canvas):
    canvas.create_oval(5, 5, 81, 81, fill='#F0E6FC', outline='')
    canvas.create_polygon(22, 39, 20, 18, 39, 31, fill='#D4BFF4', outline='#A18AC4', width=2)
    canvas.create_polygon(48, 31, 67, 18, 66, 42, fill='#D4BFF4', outline='#A18AC4', width=2)
    canvas.create_oval(19, 29, 68, 72, fill='#E2D2FA', outline='#A18AC4', width=2)
    for x in (32, 55):
        canvas.create_oval(x-2, 45, x+2, 51, fill=INK, outline='')
    for x in (26, 54):
        canvas.create_oval(x, 54, x+9, 60, fill='#F4B9D0', outline='')
    canvas.create_line(39, 56, 43, 60, 47, 56, smooth=True, fill=INK, width=2)
    canvas.create_text(77, 18, text='✦', fill='#D8B674', font=('Segoe UI', 17))
