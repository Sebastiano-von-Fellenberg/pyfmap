import numpy as np
import matplotlib.pyplot as plt
import ehtim as eh
import time 

import sys
from PyQt5.QtCore import pyqtSignal

from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QLineEdit, QPushButton,QCheckBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import pandas as pd

def load_ehtim(filename):
    obs = eh.obsdata.load_uvfits(filename)
    obs.add_scans()
    return obs

def get_baseline(obsdata, t1, t2):
    amp = obsdata.unpack_bl(t1, t2, "amp", debias=False)
    vis = obsdata.unpack_bl(t1, t2, "phase", debias=False)
    return amp, vis
    
def find_nearest_idx(array, value):
    """Find the index of the nearest value in the array."""
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx 


class MatplotlibWidget(QWidget):
    def __init__(self, mainwindow, parent=None):
        super().__init__(parent)
        
        self.mainwindow = mainwindow
        
        # Create a Figure and an Axes
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
    
        # Create a QVBoxLayout to hold the Matplotlib widget
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)

        self.setLayout(layout)

        # Plot some data
        self.plot_data()

    def plot_data(self, data_list=None, scopes_names=None, plottype='amp'):
        if data_list is None:
            # Clear the previous plot and plot new data
            self.figure.clear()

            # Redraw the canvas
            self.canvas.draw()
        else:
            self.rs_flag = []
            self.rs_unflag = []
            self.rs2_list = []
            self.data_list = data_list
            if plottype == 'phase-amp':
                print("not implemented")
            elif plottype == 'amp':
                self.fig, self.axes = plt.subplots(len(data_list), 1, sharex=True, gridspec_kw={"hspace":0})
                if len(data_list) == 1:
                    self.axes = [self.axes]
                if scopes_names is not None:
                    self.axes[0].set_title(scopes_names[0]+'-'+scopes_names[1])
                    
                for n in range(len(data_list)):
                    
                    self.axes[n].plot(data_list[n]["phase"]['time'], data_list[n]["amp"]['amp'], ".", zorder=0)
                    self.axes[n].set_ylabel('Amp [Jy]')
                    self.axes[n].set_ylim((np.nanmin(data_list[n]["amp"]['amp']), np.nanmax(data_list[n]["amp"]['amp'])))
                        
                    # Enable rectangle selector
                    self.flagselection_active = False
                    rs_flag = RectangleSelector(self.axes[n], self.on_flags_select)
                                           # unforentuaelty the rectangle is not show in this latest version, so I am expliclity drawing on in the on_flags_select function

                    rs_flag.set_active(False)
                    

                    self.rs_flag.append(rs_flag)
                    
                    self.unflagselection_active = False
                    rs_unflag = RectangleSelector(self.axes[n], self.on_unflags_select)
                                           # unforentuaelty the rectangle is not show in this latest version, so I am expliclity drawing on in the on_flags_select function

                    rs_unflag.set_active(False)                    
                    self.rs_unflag.append(rs_unflag)
                      # Initially inactive
                    
                    # Enable rectangle selector
                    self.rs2_list.append(None)
                self.axes[len(data_list)-1].set_xlabel('Time [UT]')
                self.canvas.figure = self.fig
                self.toolbar = NavigationToolbar(self.canvas, self)
                self.canvas.draw()
            else:
                print("Not implemented yet")
        
    def update_plot(self, obsdata, selected_scopes, plottype='amp'):
        # Clear the previous plot and plot new data
        if len(selected_scopes)  == 2:
            amp, phi = get_baseline(obsdata, selected_scopes[0], selected_scopes[1])
            self.plot_data(data_list=[{"amp":amp, "phase":phi}], scopes_names=(selected_scopes[0], selected_scopes[1]), plottype=plottype)
        else:
            data_list, scope_names = [], []
            for n in range(1, len(selected_scopes)):

                amp, phi = get_baseline(obsdata, selected_scopes[0], selected_scopes[n])
                data_list.append({"amp":amp, "phase":phi})
                scope_names.append((selected_scopes[0], selected_scopes[n]))
            self.plot_data(data_list=data_list, scopes_names=None, plottype=plottype)
            

    def on_flags_select(self, eclick, erelease):
        if self.flagselection_active:
            for n, ax in enumerate(self.axes):
                if eclick.inaxes == ax:
                    num = n
                for patch in ax.patches:
                    patch.remove()
                
            flagged_telescope = self.mainwindow.scopes_names[num]
            
            # Get the coordinates of the selected rectangle
            xmin, xmax = min(eclick.xdata, erelease.xdata), max(eclick.xdata, erelease.xdata)
            ymin, ymax = min(eclick.ydata, erelease.ydata), max(eclick.ydata, erelease.ydata) 
            
            
            # Get data points within the selected rectangle
            
            x_data = self.data_list[num]["phase"]['time']
            y_data = self.data_list[num]["amp"]['amp']

            rect = plt.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin, fill=True, facecolor='xkcd:light blue', edgecolor='xkcd:light blue', linewidth=2, alpha=0.2)
            self.axes[num].add_patch(rect)
            
            mask = (x_data >= xmin) & (x_data <= xmax) & (y_data >= ymin) & (y_data <= ymax)
            selected_x = x_data[mask]
            selected_y = y_data[mask]
            self.axes[num].plot(selected_x, selected_y, 'x', color='xkcd:dark red')
            sorted_xdata = np.sort(x_data)
            flag_starttime = []
            flag_stoptime = []

            for x in zip(selected_x):
                idx = find_nearest_idx(sorted_xdata, x)
                if idx > 1: 
                    ts = sorted_xdata[idx] - (sorted_xdata[idx] - sorted_xdata[idx-1])/2
                else:
                    ts = sorted_xdata[0]
                
                if idx < len(sorted_xdata):
                    te = sorted_xdata[idx] + (sorted_xdata[idx+1] - sorted_xdata[idx])/2
                else:
                    te = sorted_xdata[-1]
                flag_starttime.append(ts[0])
                flag_stoptime.append(te[0])
            
            
            df = pd.DataFrame({"telescope1":np.repeat(flagged_telescope, len(flag_starttime)), 
                               "telescope2":np.repeat("None", len(flag_starttime)),
                               "starttime":flag_starttime,  
                               "endtime":flag_stoptime})
            self.mainwindow.flagfile = pd.concat([self.mainwindow.flagfile, df], axis=0, ignore_index=True)
            self.mainwindow.flagfile = self.mainwindow.flagfile.drop_duplicates()
            print(self.mainwindow.flagfile)
                
                
        ## WARNING Currently nothing implemented for phase flagging
        
        self.canvas.draw()
        
        
    def on_unflags_select(self, eclick, erelease):
        if self.unflagselection_active:
            for n, ax in enumerate(self.axes):
                if eclick.inaxes == ax:
                    num = n
                for patch in ax.patches:
                    patch.remove()
                
            unflagged_telescope = self.mainwindow.scopes_names[num]
            
            # Get the coordinates of the selected rectangle
            xmin, xmax = min(eclick.xdata, erelease.xdata), max(eclick.xdata, erelease.xdata)
            ymin, ymax = min(eclick.ydata, erelease.ydata), max(eclick.ydata, erelease.ydata) 
            
            
            # Get data points within the selected rectangle
            
            x_data = self.data_list[num]["phase"]['time']
            y_data = self.data_list[num]["amp"]['amp']

            rect = plt.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin, fill=True, facecolor='xkcd:light green', edgecolor='xkcd:light green', linewidth=2, alpha=0.2)
            self.axes[num].add_patch(rect)
            
            

            mask = (x_data >= xmin) & (x_data <= xmax) & (y_data >= ymin) & (y_data <= ymax)
            selected_x = x_data[mask]
            selected_y = y_data[mask]
            
            sorted_xdata = np.sort(x_data)
            unflag_starttime = []
            unflag_stoptime = []

            for x in zip(selected_x):
                idx = find_nearest_idx(sorted_xdata, x)
                if idx > 1: 
                    ts = sorted_xdata[idx] - (sorted_xdata[idx] - sorted_xdata[idx-1])/2
                else:
                    ts = sorted_xdata[0]
                
                if idx < len(sorted_xdata):
                    te = sorted_xdata[idx] + (sorted_xdata[idx+1] - sorted_xdata[idx])/2
                else:
                    te = sorted_xdata[-1]
                unflag_starttime.append(ts[0])
                unflag_stoptime.append(te[0])
            
            
            df = pd.DataFrame({"telescope1":np.repeat(unflagged_telescope, len(unflag_starttime)), 
                               "telescope2":np.repeat("None", len(unflag_starttime)),
                               "starttime":unflag_starttime,  
                               "endtime":unflag_stoptime})

            print('unflagging following dat')
                
        ## WARNING Currently nothing implemented for phase flagging
        
        self.canvas.draw()


class MatplotlibWidget2(QWidget):
    def __init__(self, mainwindow, parent=None):
        super().__init__(parent)
        
        self.mainwindow = mainwindow
        
        self.lastclick = time.time()
        # Create a Figure and an Axes
        self.figure = Figure(figsize=(5,5))
        self.canvas = FigureCanvas(self.figure)
        
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.clicked_points = []
        self.clicked_scopes = []
        
        # Create a NavigationToolbar
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Create checkboxes for options

        
        
        # Create a QVBoxLayout to hold the Matplotlib widget and the toolbar
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)
        self.setLayout(layout)
        
        
        # Plot some data
        self.plot_telescopes()
        

    def plot_telescopes(self, obs=None, draw=True):
        if obs is None:
            # Clear the previous plot and plot new data
            self.figure.clear()

            # Redraw the canvas
            self.canvas.draw()
        else:
            self.scopes = obs.tkey
            self.scopes_names = np.array(list(obs.tkey.keys()))
            self.positions = np.array([np.random.uniform(0, 10, len(self.scopes)),
                                       np.random.uniform(0, 10, len(self.scopes))])

            # Clear the previous plot and plot new data
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            for num, s in enumerate(self.scopes):
                ax.plot(self.positions[0, num], self.positions[1, num], "o", ms=5, color="k")
                ax.annotate(s, xy=(self.positions[0, num], self.positions[1, num]), color="k")
                
            ax.set_xlim((-2, 12))
            ax.set_ylim((-2, 12))
            
            if draw:
                # Redraw the canvas
                self.canvas.draw()
            else:
                return ax

    def on_click(self, event):
        if event.inaxes:
            # Check if the click was inside the plot area
            x, y = event.xdata, event.ydata
            if event.button == 1:
                distance = np.sqrt((x-self.positions[0])**2 + (y-self.positions[1])**2) 
                if np.min(distance) < 0.5:
                    self.clicked_points.append((self.positions[0, np.argmin(distance)], 
                                                self.positions[1, np.argmin(distance)]))
                    
                    self.clicked_scopes.append(self.scopes_names[np.argmin(distance)])
                    # Clear the previous plot and plot new data
                    self.figure.clear()
                    ax = self.figure.add_subplot(111)
                    
                    for num, s in enumerate(self.scopes):
                        ax.plot(self.positions[0, num], self.positions[1, num], "o", ms=5, color="k")
                        ax.annotate(s, xy=(self.positions[0, num], self.positions[1, num]), color="k")
                    if self.clicked_points:
                        x_points, y_points = zip(*self.clicked_points)
                        ax.scatter(x_points, y_points, color='red', label='Selected Points', zorder=5)
                        for xx, yy in zip(x_points, y_points):
                            ax.plot([x_points[0], xx], [y_points[0], yy], "-", color="k")

                    ax.set_xlim((-2, 12))
                    ax.set_ylim((-2, 12))
                    
                    # Redraw the canvas
                    self.canvas.draw()
                    if len(self.clicked_scopes) == 2:
                        self.mainwindow.matplotlib_widget.update_plot(self.mainwindow.obsdata, self.clicked_scopes)
                    elif len(self.clicked_scopes) > 2:
                        self.mainwindow.matplotlib_widget.update_plot(self.mainwindow.obsdata, self.clicked_scopes)
                        
                    
            if event.button == 3:
                self.clicked_points  = []
                self.clicked_scopes = []
                self.figure.clear()
                ax = self.figure.add_subplot(111)
                
                for num, s in enumerate(self.scopes):
                    ax.plot(self.positions[0, num], self.positions[1, num], "o", ms=5, color="k")
                    ax.annotate(s, xy=(self.positions[0, num], self.positions[1, num]), color="k")

                    
                ax.set_xlim((-2, 12))
                ax.set_ylim((-2, 12))
                
                # Redraw the canvas
                self.canvas.draw()
                
class ButtonWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create two QPushButton instances
        self.button1 = QPushButton('Flag data', self)
        self.button2 = QPushButton('Unflag data', self)

        # Arrange the buttons in a horizontal layout
        layout = QHBoxLayout()
        
        self.checkbox_stationflag  = QCheckBox("Station Flag", self)
        self.checkbox_baselineflag = QCheckBox("Baseline Flag", self)

        layout.addWidget(self.button1)
        layout.addWidget(self.button2)
        layout.addWidget(self.checkbox_stationflag)
        layout.addWidget(self.checkbox_baselineflag)
        

        self.setLayout(layout)
        
        #/aux/vcompute2a/sfellenberg/workspace/RXJ1301/reduce4/RXJ1301.9+27_calibrated.uvf
        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create a QLineEdit for entering a string
        self.input_text = QLineEdit(self)
        #self.input_text.setPlaceholderText('/aux/vcompute2a/sfellenberg/workspace/RXJ1301/reduce4/RXJ1301.9+27_calibrated.uvf')
        #self.input_text.setText('/aux/vcompute2a/sfellenberg/workspace/RXJ1301/reduce4/RXJ1301.9+27_calibrated.uvf')
        self.input_text.setText('/home/sebastiano/Documents/PythonScripts/RXJ1301.9+27_calibrated.uvf')
        self.input_text.returnPressed.connect(self.plot_with_text)
        
        self.flagfile = pd.DataFrame()
        self.flagfile["telescope1"] = pd.Series([], dtype=str)
        self.flagfile["telescope2"] = pd.Series([], dtype=str)
        self.flagfile["starttime"]  = pd.Series([], dtype=float)
        self.flagfile["endtime"]    = pd.Series([], dtype=float)
        
        
        # Create a MatplotlibWidget instance and set it as the central widget
        self.matplotlib_widget = MatplotlibWidget(self)
        self.setCentralWidget(self.matplotlib_widget)
        
        self.matplotlib_widget2 = MatplotlibWidget2(self)


        # Create a QPushButton to trigger loading ehtim
        self.load_ehtim_button = QPushButton('load file', self)
        self.load_ehtim_button.clicked.connect(self.trigger_load_ehtim)
    
        # Create a ButtonWidget instance
        self.button_widget = ButtonWidget(self)
        self.button_widget.button1.clicked.connect(self.toggle_rectangle_flagselection)
        self.button_widget.button2.clicked.connect(self.toggle_rectangle_unflagselection)

        # Arrange the widgets in a layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.input_text)
        button_layout.addWidget(self.load_ehtim_button)
        
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.matplotlib_widget)
        main_layout.addWidget(self.matplotlib_widget2)  # Add the second plot widget

        
        # Create a new widget to hold the layout with buttons
        button_widget_container = QWidget()
        button_widget_container.setLayout(main_layout)
        
        # Arrange the button widget and the main layout in a horizontal layout
        layout = QHBoxLayout()
        layout.addWidget(button_widget_container)
        layout.addWidget(self.button_widget)
        
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        
        self.setWindowTitle('pyDifmap')
        self.setGeometry(100, 100, 800, 600)
        
    def trigger_load_ehtim(self):
        text = self.input_text.text()
        self.obsdata = load_ehtim(text)
        self.scopes = self.obsdata.tkey
        self.scopes_names = np.array(list(self.obsdata.tkey.keys()))
        amp, phi = get_baseline(self.obsdata, self.scopes_names[0], self.scopes_names[1], )
        self.matplotlib_widget.plot_data(data_list=[{"amp":amp, "phase":phi}], plottype='amp')
        self.matplotlib_widget2.plot_telescopes(obs=self.obsdata)
        
        
    def plot_with_text(self):
        text = self.input_text.text()
        self.matplotlib_widget.plot_data(text)

    def toggle_rectangle_flagselection(self):
        self.matplotlib_widget.flagselection_active = not self.matplotlib_widget.flagselection_active
    
        for n in range(len(self.matplotlib_widget.rs_flag)):
            if self.matplotlib_widget.rs_flag is not None:
                self.matplotlib_widget.rs_flag[n].set_active(self.matplotlib_widget.flagselection_active)
        
        for n in range(len(self.matplotlib_widget.rs2_list)):
            if self.matplotlib_widget.rs2_list[n] is not None:
                self.matplotlib_widget.rs2_list[n].set_active(self.matplotlib_widget.flagselection_active)

        if self.matplotlib_widget.flagselection_active:
            print("Rectangle flag selection mode active. Select a rectangle on the plot.")
        else:
            print("Rectangle flag selection mode deactivated.")



    def toggle_rectangle_unflagselection(self):
        self.matplotlib_widget.unflagselection_active = not self.matplotlib_widget.unflagselection_active
    
        for n in range(len(self.matplotlib_widget.rs_flag)):
            if self.matplotlib_widget.rs_unflag is not None:
                print("setting active!")
                self.matplotlib_widget.rs_unflag[n].set_active(self.matplotlib_widget.unflagselection_active)
        

        if self.matplotlib_widget.unflagselection_active:
            print("Rectangle unflag selection mode active. Select a rectangle on the plot.")
        else:
            print("Rectangle unflag selection mode deactivated.")
            
            
            
    def update_matplotlib_widget(self, selected_points):
        # Call the update_plot method in MatplotlibWidget
        self.matplotlib_widget.update_plot(selected_points)
        
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
