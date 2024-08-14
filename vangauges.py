import tkinter as tk
import tk_tools
from tk_tools.images import rotary_gauge_volt, rotary_scale
import random


max_value = 100.0
min_value = 0.0


RPM_MAX = 6000
RPM_MIN = 0
EGT_MAX = 1000
EGT_MIN = 0
IAT_MAX = 150
IAT_MIN = 0
IAP_MAX = 2
IAP_MIN = -1
OFP_MAX = 10    #oil filter pressure
OFP_MIN = 0
VBATT_MAX = 15
VBATT_MIN = 10

mv_RPM = 5000
mv_manifold = 50
mv_precat = 50
mv_postcat = 50
mv_iat = 50
mv_iap = 0.0
mv_ofp = 0.0
mv_voltage = 10.0


def increment():
    global value

    value += increment_value
    if value > max_value:
        value = max_value

    p1.set_value(value)
    p2.set_value(value)
    p3.set_value(value)


def decrement():
    global value
    value -= increment_value

    if value < min_value:
        value = min_value

    p1.set_value(value)
    p2.set_value(value)
    p3.set_value(value)


def random_updates():
    global mv_RPM
    print("update")
    mv_RPM = mv_RPM + random.randint(-50, 50)
    gaugeRPM.set_value(mv_RPM)



    root.after(1000, random_updates)

if __name__ == '__main__':

    root = tk.Tk()
    root.geometry("800x480")
    root.attributes('-fullscreen',True)
    root.title("Van Dash")

    l1 = tk.Label(root, text = "RPM")
    l1.grid(row=0, column=0)

    l2 = tk.Label(root, text = "MANIFOLD")
    l2.grid(row=0, column=1)

    l3 = tk.Label(root, text = "PRECAT")
    l3.grid(row=0, column=2)

    l4 = tk.Label(root, text = "POSTCAT")
    l4.grid(row=0, column=3)

    gaugeRPM = tk_tools.RotaryScale(root, 
                            max_value=RPM_MAX, 
                            size=100,
                            needle_thickness=3,
                            needle_color='black',
                            unit=None,
                            img_data=rotary_gauge_bar)
    gaugeRPM.grid(row=1, column=0)

    gaugeManifold = tk_tools.RotaryScale(root, 
                            max_value=EGT_MAX, 
                            size=100,
                            needle_thickness=3,
                            needle_color='black',
                            unit=None)
    gaugeManifold.grid(row=1, column=1)

    gaugePreCat = tk_tools.RotaryScale(root, 
                            max_value=EGT_MAX, 
                            size=100,
                            needle_thickness=3,
                            needle_color='black',
                            unit=None)
    gaugePreCat.grid(row=1, column=2)

    gaugePostCat = tk_tools.RotaryScale(root, 
                            max_value=EGT_MAX, 
                            size=100,
                            needle_thickness=3,
                            needle_color='black',
                            unit=None)
    gaugePostCat.grid(row=1, column=3)




    increment_value = 1.0
    value = 0.0
    '''
    inc_btn = tk.Button(root,
                        text='increment_value by {}'.format(increment_value),
                        command=increment)

    inc_btn.grid(row=1, column=0, columnspan=2, sticky='news')

    dec_btn = tk.Button(root,
                        text='decrement by {}'.format(increment_value),
                        command=decrement)

    dec_btn.grid(row=2, column=0, columnspan=2, sticky='news')
    '''
    root.after(1000, random_updates)
    root.mainloop()
