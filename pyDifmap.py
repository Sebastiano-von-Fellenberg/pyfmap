import numpy as np
import matplotlib.pyplot as plt
import ehtim as eh


import sys
from PyQt5.QtCore import pyqtSignal

from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QLineEdit, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


def load_ehtim(filename):
    obs = eh.obsdata.load_uvfits(filename)
    obs.add_scans()
    return obs

def get_baseline(obsdata, t1, t2):
    amp = obsdata.unpack_bl(t1, t2, "amp", debias=False)
    vis = obsdata.unpack_bl(t1, t2, "phase", debias=False)
    return amp, vis
    


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
            if plottype == 'phase-amp':
                ax1 = self.figure.add_subplot(111)
                if scopes_names is not None:
                    ax1.set_title(scopes_names[0]+'-'+scopes_names[1])
                for n in range(len(data_list)):
                    ax1.plot(data_list[n]["phase"]['time'], data_list[n]["phase"]['phase'], ".")
                ax1.set_xlabel('Time [UT]')
                ax1.set_ylabel('Amp [Jy]')
                #ax1.set_xlim((np.nanmin(data_list[0]['time']), np.nanmax(data_list[0]['time'])))
                #ax1.set_ylim((np.nanmin(data_list[0]['amp']), np.nanmax(data_list[0]['amp'])))
                            
                ax2 = self.figure.add_subplot(211)
                for n in range(len(data_list)):
                    ax2.plot(data_list[n]["amp"]['time'], data_list[n]["amp"]['amp'], ".")
                ax2.set_xlabel('Time [UT]')
                ax2.set_ylabel('Phase [deg]')
                #ax2.set_xlim((np.nanmin(data_list[0]['time']), np.nanmax(data_list[0]['time'])))
                #ax2.set_ylim((-180, 180))
                
                self.selection_active = False
                self.rs1 = RectangleSelector(
                    ax1, self.on_rectangle_select, drawtype='box',
                    rectprops=dict(facecolor='blue', edgecolor='black', alpha=0.5, fill=True)
                )
                self.rs1.set_active(False)  # Initially inactive

                self.rs2 = RectangleSelector(
                    ax2, self.on_rectangle_select, drawtype='box',
                    rectprops=dict(facecolor='blue', edgecolor='black', alpha=0.5, fill=True)
                )
                self.rs2.set_active(False)  # Initially inactive
                
                self.canvas.draw()
            elif plottype == 'amp':
                ax1 = self.figure.add_subplot(111)
                if scopes_names is not None:
                    ax1.set_title(scopes_names[0]+'-'+scopes_names[1])
                for n in range(len(data_list)):
                    ax1.plot(data_list[n]["phase"]['time'], data_list[n]["phase"]['phase'], ".")
                ax1.set_xlabel('Time [UT]')
                ax1.set_ylabel('Amp [Jy]')
                #ax1.set_xlim((np.nanmin(data_list[0]['time']), np.nanmax(data_list[0]['time'])))
                #ax1.set_ylim((np.nanmin(data_list[0]['amp']), np.nanmax(data_list[0]['amp'])))
            
                
                # Enable rectangle selector
                self.selection_active = False
                self.rs1 = RectangleSelector(
                    ax1, self.on_rectangle_select, drawtype='box',
                    rectprops=dict(facecolor='blue', edgecolor='black', alpha=0.5, fill=True)
                )
                self.rs1.set_active(False)  # Initially inactive
                
                # Enable rectangle selector
                self.rs2 = None 
                
                self.canvas.draw()
            else:
                ax2 = self.figure.add_subplot(111)
                for n in range(len(data_list)):
                    ax2.plot(data_list[n]["phase"]['time'], data_list[n]["phase"]['phase'], ".")      
                ax2.set_xlabel('Time [UT]')
                ax2.set_ylabel('Phase [deg]')
                #ax2.set_xlim((np.nanmin(data_list[0]['time']), np.nanmax(data_list[0]['time'])))
                #ax2.set_ylim((-180, 180))
                
                # Enable rectangle selector
                self.selection_active = False
                self.rs1 = None 
                
                # Enable rectangle selector
                self.rs2 = RectangleSelector(
                    ax2, self.on_rectangle_select, drawtype='box',
                    rectprops=dict(facecolor='blue', edgecolor='black', alpha=0.5, fill=True)
                )
                self.rs2.set_active(False)  # Initially inactive
        
    def update_plot(self, obsdata, selected_scopes):
        # Clear the previous plot and plot new data
        if len(selected_scopes)  == 2:
            amp, phi = get_baseline(obsdata, selected_scopes[0], selected_scopes[1])
            self.plot_data(data_list=[{"amp":amp, "phase":phi}], scopes_names=(selected_scopes[0], selected_scopes[1]))
        else:
            data_list = [{"amp":selected_scopes[0], "phase":selected_scopes[n]} for n in range(1, len(selected_scopes))]
            
            
        
    def on_rectangle_select(self, eclick, erelease):
        if self.selection_active:
            try:
                # Get the coordinates of the selected rectangle
                xmin, xmax = min(eclick.xdata, erelease.xdata), max(eclick.xdata, erelease.xdata)
                ymin, ymax = min(eclick.ydata, erelease.ydata), max(eclick.ydata, erelease.ydata)

                # Get data points within the selected rectangle
                x_data, y_data = self.rs1.get_verts().T
                mask = (x_data >= xmin) & (x_data <= xmax) & (y_data >= ymin) & (y_data <= ymax)
                selected_x = x_data[mask]
                selected_y = y_data[mask]

                # Print the selected data points
                print("Selected data points:")
                for x, y in zip(selected_x, selected_y):
                    print(f"x: {x}, y: {y}")
            except:
                print("Not selected amp data")
        
            try:
                # Get the coordinates of the selected rectangle
                xmin, xmax = min(eclick.xdata, erelease.xdata), max(eclick.xdata, erelease.xdata)
                ymin, ymax = min(eclick.ydata, erelease.ydata), max(eclick.ydata, erelease.ydata)

                # Get data points within the selected rectangle
                x_data, y_data = self.rs2.get_verts().T
                mask = (x_data >= xmin) & (x_data <= xmax) & (y_data >= ymin) & (y_data <= ymax)
                selected_x = x_data[mask]
                selected_y = y_data[mask]

                # Print the selected data points
                print("Selected data points:")
                for x, y in zip(selected_x, selected_y):
                    print(f"x: {x}, y: {y}")
            except:
                print("Not selected phase data")
            

class MatplotlibWidget2(QWidget):
    def __init__(self, mainwindow, parent=None):
        super().__init__(parent)
        
        self.mainwindow = mainwindow
        
        
        # Create a Figure and an Axes
        self.figure = Figure(figsize=(5,5))
        self.canvas = FigureCanvas(self.figure)
        
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.clicked_points = []
        self.clicked_scopes = []
        
        # Create a NavigationToolbar
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Create a QVBoxLayout to hold the Matplotlib widget and the toolbar
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)
        self.setLayout(layout)

        # Plot some data
        self.plot_data()

    def plot_data(self, obs=None):
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
            
            # Redraw the canvas
            self.canvas.draw()

    def on_click(self, event):
        if event.inaxes:
            # Check if the click was inside the plot area
            x, y = event.xdata, event.ydata
            if event.button == 1:
                distance = np.sqrt((x-self.positions[0])**2 + (y-self.positions[1])**2) 
                if np.min(distance) < 0.5:
                    print(self.scopes_names)
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
                        ax.scatter(x_points, y_points, color='red', label='Selected Points')

                    ax.set_xlim((-2, 12))
                    ax.set_ylim((-2, 12))
                    
                    # Redraw the canvas
                    self.canvas.draw()
                    if len(self.clicked_scopes) == 2:
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
        layout.addWidget(self.button1)
        layout.addWidget(self.button2)
        self.setLayout(layout)
        
        #/aux/vcompute2a/sfellenberg/workspace/RXJ1301/reduce4/RXJ1301.9+27_calibrated.uvf
        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create a QLineEdit for entering a string
        self.input_text = QLineEdit(self)
        self.input_text.setPlaceholderText('Filename')
        self.input_text.returnPressed.connect(self.plot_with_text)
        
        # Create a MatplotlibWidget instance and set it as the central widget
        self.matplotlib_widget = MatplotlibWidget(self)
        self.setCentralWidget(self.matplotlib_widget)
        
        self.matplotlib_widget2 = MatplotlibWidget2(self)


        # Create a QPushButton to trigger loading ehtim
        self.load_ehtim_button = QPushButton('load file', self)
        self.load_ehtim_button.clicked.connect(self.trigger_load_ehtim)
    
        # Create a ButtonWidget instance
        self.button_widget = ButtonWidget(self)
        self.button_widget.button1.clicked.connect(self.toggle_rectangle_selection)


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
        amp, phi = get_baseline(self.obsdata, "EB", "LA")
        self.matplotlib_widget.plot_data(data_list=[{"amp":amp, "phase":phi}])
        self.matplotlib_widget2.plot_data(obs=self.obsdata)
        
    def plot_with_text(self):
        text = self.input_text.text()
        self.matplotlib_widget.plot_data(text)

    def toggle_rectangle_selection(self):
        self.matplotlib_widget.selection_active = not self.matplotlib_widget.selection_active
        self.matplotlib_widget.rs1.set_active(self.matplotlib_widget.selection_active)
        self.matplotlib_widget.rs2.set_active(self.matplotlib_widget.selection_active)

        if self.matplotlib_widget.selection_active:
            print("Rectangle selection mode active. Select a rectangle on the plot.")
        else:
            print("Rectangle selection mode deactivated.")

    def update_matplotlib_widget(self, selected_points):
        # Call the update_plot method in MatplotlibWidget
        self.matplotlib_widget.update_plot(selected_points)
        
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
