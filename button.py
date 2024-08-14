from tkinter import * 
import matplotlib.pyplot as plt
from matplotlib.figure import Figure 
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk) 

from tkinter import ttk
import sv_ttk

# plot function is created for  
# plotting the graph in  
# tkinter window 
def plot(): 
    plt.rcParams['toolbar'] = 'None'
    plt.style.use('dark_background')
    
    # the figure that will contain the plot 
    fig = plt.Figure(figsize = (5, 5), 
                 dpi = 100) 

    # list of squares 
    y = [i**2 for i in range(101)] 
  
    # adding the subplot 
    plot1 = fig.add_subplot(111) 
  
    # plotting the graph 
    plot1.plot(y) 
  
    # creating the Tkinter canvas 
    # containing the Matplotlib figure 
    canvas = FigureCanvasTkAgg(fig, 
                               master = window)   
    canvas.draw() 
  
    # placing the canvas on the Tkinter window 
    canvas.get_tk_widget().pack()
  
    # creating the Matplotlib toolbar 
    toolbar = NavigationToolbar2Tk(canvas, 
                                   window) 
    toolbar.update() 
  
    # placing the toolbar on the Tkinter window 
    canvas.get_tk_widget().pack()

def quit_app():
    quit()

# the main Tkinter window 
window = Tk() 
  
# setting the title  
window.title('Plotting in Tkinter') 
  
# dimensions of the main window 
window.geometry("500x500") 
  
# button that displays the plot 
plot_button = ttk.Button(window,  
                     command = plot,  
                     text = "Plot") 

# button that displays the plot 
quit_button = ttk.Button(window,  
                     command = quit_app,  
                     text = "Quit") 

plot_button.pack(side=LEFT)
quit_button.pack(side=LEFT)

# This is where the magic happens
sv_ttk.set_theme("dark")  

# run the gui 
window.mainloop() 