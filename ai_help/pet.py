import tkinter as tk


class Pet(tk.Canvas):
    """A vector cat with idle blinking and a thinking animation."""
    def __init__(self, parent, scale=1, background='#F7F5FF'):
        super().__init__(parent, width=int(94*scale), height=int(100*scale), bg=background, highlightthickness=0)
        self.drawing_scale = scale
        self.thinking, self.frame = False, 0
        self.after(80, self.animate)

    def animate(self):
        self.frame += 1
        self.draw()
        self.after(120, self.animate)

    def draw(self):
        self.delete('all')
        lift = 2 if self.thinking and self.frame % 8 < 4 else 0
        self.create_oval(17, 85, 81, 96, fill='#E7E0F5', outline='')
        for points in ((18, 41, 18, 11, 39, 27), (57, 27, 77, 11, 79, 42)):
            self.create_polygon(*[value-lift if i % 2 else value for i, value in enumerate(points)], fill='#C8B8FA', outline='#8D79C3', width=2)
        self.create_oval(16, 25-lift, 81, 89-lift, fill='#DDD2FF', outline='#8D79C3', width=2)
        for x in (26, 60):
            self.create_oval(x, 59-lift, x+13, 67-lift, fill='#F3B8D2', outline='')
        for x in (36, 61):
            if self.frame % 50 in (0, 1):
                self.create_line(x-3, 51-lift, x+3, 51-lift, fill='#493E64', width=2)
            else:
                self.create_oval(x-3, 47-lift, x+3, 55-lift, fill='#493E64', outline='')
        self.create_line(45, 62-lift, 49, 65-lift, 53, 62-lift, fill='#493E64', smooth=True, width=2)
        if self.thinking:
            self.create_text(84, 14, text='·' * (self.frame // 4 % 3 + 1), fill='#8D79C3', font=('Segoe UI', max(1, round(15*self.drawing_scale)), 'bold'))
        if self.drawing_scale != 1:
            self.scale('all', 0, 0, self.drawing_scale, self.drawing_scale)
