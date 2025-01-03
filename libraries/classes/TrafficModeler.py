import numpy as np
import pandas as pd
import sumolib
from matplotlib import pyplot as plt

from libraries.constants import MODEL_DATA_FILE_PATH

class TrafficModeler:
    """
    A class that manages and compares traffic patterns based on the actual data provided as input

    Attributes:
        trafficDataFile (pandas DataFrame): dataframe containing traffic measurement.
        sumoNet (sumolib.net): sumolib class that contains the road network information representable on SUMO
    """

    trafficData: []
    sumoNet: sumolib.net
    modelType: str
    def __init__(self, trafficDataFile: str, sumoNetFile : str, date: str = None, timeSlot: str = '00:00-23:00', modelType: str = "greenshield"):
        """
        Initializes the TrafficModeler, also deriving road parameters from the SUMO network

        :param trafficDataFile (str): path of the file containing traffic measurement.
        :param sumoNetFile (str): path of the file related to the sumo network (identified with the extension .net.xml).
        :param timeSlot (str): Time window value of the measurements to be evaluated reported in the format hh:mm-hh:mm
        :param modelType (str): Name of the traffic model to apply
        """

        trafficDataDf = pd.read_csv(trafficDataFile, sep=';')
        if date is not None:
            trafficDataDf = trafficDataDf[trafficDataDf['data'].str.contains(date)]
        self.sumoNet = sumolib.net.readNet(sumoNetFile)
        self.modelType = modelType
        self.trafficData = []
        for index, row in trafficDataDf.iterrows():
            edge_id = row["edge_id"]
            edge = self.sumoNet.getEdge(edge_id)
            length = edge.getLength()
            vMax = edge.getSpeed()
            laneCount = len(edge.getLanes())
            vehicleLength = 7.5 #7.5 # this length is including the gap between vehicles
            maxDensity = laneCount / vehicleLength
            print(f"Edge {edge_id}: k_jam = {maxDensity * 1000} vehicles/km")
            first = int(timeSlot[:2])
            last = int(timeSlot[6:8])
            # Calculate the vehicle count for the specified time slot
            if last - first > 1:  # If the time slot spans multiple hours
                total_count = sum(row[f"{hour:02d}:00-{(hour + 1) % 24:02d}:00"] for hour in range(first, last))
                flow = str(total_count)
            else:
                flow = str(row[timeSlot])

            vps = int(flow) / (3600 * (last - first))  # flow is set as vehicles per second
            density = vps / vMax
            laneDensity = density / laneCount
            laneVps = vps / laneCount
            density = vps / vMax
            if self.modelType == "greenshield":
                velocity = vMax * (1 - density / maxDensity)
            elif self.modelType == "underwood":
                velocity = vMax * np.exp(density / maxDensity)
            density = vps / velocity if velocity > 0 else maxDensity
            density = density / laneCount
            normVelocity = velocity / vMax
            vpsPerLane = vps / laneCount

            self.trafficData.append({
                "edge_id": edge_id,
                "length": length,
                "laneCount": laneCount,
                "flow": flow,
                "vehiclesPerSecond": vps,
                "vpsPerLane": vpsPerLane,
                "laneVps": laneVps,
                "density": density,
                "laneDensity": laneDensity,
                "maxDensity": maxDensity,
                "vMax": vMax,
                "velocity": velocity,
                "normVelocity": normVelocity
            })



    def saveTrafficData(self, outputDataPath: str = MODEL_DATA_FILE_PATH):
    # TODO: set a name convention for saving new model data (e.g. greenshield_01-02-2024_00:00-23:00)
        """
        Save current traffic information stored inside the TrafficModeler into a .csv file
        Args:
            outputDataPath: path of the file to save the traffic model data
        """
        print("Saving...")
        df = pd.DataFrame(self.trafficData)
        df.to_csv(outputDataPath, sep=';', index=False, float_format='%.4f', decimal=',')
        print("New Model data saved into: " + outputDataPath + " file")

    # TODO: plotModel should also report some values for similarity
    def plotModel(self):
        """
        function that plots the values of flux, density and velocity against each other in three graphs.
        The values are compared with the traffic model chosen at the initialization stage
        """
        print("Plotting the data according to theoretical model...")

        df = pd.DataFrame(self.trafficData)
        # unique values of max speed
        unique_vmax = df["vMax"].unique()

        # Crea tre figure per i tre tipi di plot
        fig1, ax1 = plt.subplots(len(unique_vmax), 1, figsize=(8, 4 * len(unique_vmax)))
        fig2, ax2 = plt.subplots(len(unique_vmax), 1, figsize=(8, 4 * len(unique_vmax)))
        fig3, ax3 = plt.subplots(len(unique_vmax), 1, figsize=(8, 4 * len(unique_vmax)))

        if len(unique_vmax) == 1:  # Garantisci che gli assi siano array anche con un solo vmax
            ax1 = [ax1]
            ax2 = [ax2]
            ax3 = [ax3]

        for i, v_max in enumerate(unique_vmax):
            # Filtra i dati per v_max corrente
            subset = df[df["vMax"] == v_max]
            v_max = (v_max * 3.6).round()
            # Calcola k_jam per ogni segmento basandosi sul numero di corsie
            # Media i valori di lane_count se ci sono più segmenti con lo stesso v_max
            avg_lane_count = subset["laneCount"].mean()
            # k_jam = 200 / avg_lane_count  # Stima densità al blocco
            # k_jam = 133 / 1000  # Densità massima (esempio: 133 veicoli/km)
            k_jam = avg_lane_count / 7.5  # Densità massima (esempio: 133 veicoli/km)
            # Dati di densità teorici (da 0 a k_jam)
            k = np.linspace(0, k_jam, 500)

            if self.modelType == "greenshield":
                v_theoretical = v_max * (1 - k / k_jam)
            elif self.modelType == "underwood":
                v_theoretical = v_max * np.exp(k / k_jam)
            q_theoretical = v_theoretical * k  # Flusso teorico

            # Flusso osservato
            q_observed = subset["velocity"] * 3.6 * subset["density"]

            # Plot Velocità-Densità
            ax1[i].plot(k, v_theoretical, label=f"Curva teorica v_max = {v_max} km/h", color='blue')
            ax1[i].scatter(subset["density"], (subset["velocity"] * 3.6), label="Dati osservati", color='orange',
                           alpha=0.7)
            ax1[i].set_title(f"Velocità-Densità (v_max = {v_max} km/h)")
            ax1[i].set_xlabel("Densità (veicoli/km)")
            ax1[i].set_ylabel("Velocità (km/h)")
            ax1[i].legend()
            ax1[i].grid()

            # Plot Flusso-Densità
            ax2[i].plot(k, q_theoretical, label=f"Curva teorica v_max = {v_max} km/h", color='green')
            ax2[i].scatter(subset["density"], q_observed, label="Dati osservati", color='red', alpha=0.7)
            ax2[i].set_title(f"Flusso-Densità (v_max = {v_max} km/h)")
            ax2[i].set_xlabel("Densità (veicoli/km)")
            ax2[i].set_ylabel("Flusso (veicoli/h)")
            ax2[i].legend()
            ax2[i].grid()

            # Plot Flusso-Velocità
            ax3[i].plot(v_theoretical, q_theoretical, label=f"Curva teorica v_max = {v_max} km/h", color='purple')
            ax3[i].scatter((subset["velocity"] * 3.6), q_observed, label="Dati osservati", color='brown', alpha=0.7)
            ax3[i].set_title(f"Flusso-Velocità (v_max = {v_max} km/h)")
            ax3[i].set_xlabel("Velocità (km/h)")
            ax3[i].set_ylabel("Flusso (veicoli/h)")
            ax3[i].legend()
            ax3[i].grid()

        # Migliora il layout delle figure
        fig1.tight_layout()
        fig2.tight_layout()
        fig3.tight_layout()

        # Mostra tutte le figure
        plt.show()

    def setModel(self, newModelType):
    # TODO: changing the model type can be useful when comparing different models with same data. It requires to iter
    # through all the measurement dataset
        print("Function to be done")

    def evaluateModel(self, outputSUMO):
    # TODO: evaluate model according to SUMO output
        print("Function to be done")
