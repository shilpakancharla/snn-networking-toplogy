import os 
import tarfile 
import networkx
import numpy as np 
from torch.utils.data import Dataset, DataLoader

class NetworkInput:
    def __init__(self, input_filepath, traffic_filepath, link_filepath, sim_filepath):
        self.input_filepath = input_filepath
        self.traffic_filepath = traffic_filepath
        self.link_filepath = link_filepath
        self.sim_filepath = sim_filepath
        
        # Data collection
        self.simulation_numbers, self.routing_matrices = self.process_input_file(self.input_filepath)
        self.max_avg_lambda_list, self.traffic_measurements = self.get_traffic_metrics(self.traffic_filepath)
        self.global_packets_list, self.global_losses_list, self.global_delay_list, self.metrics_list = self.get_simulation_metrics(self.sim_filepath)
        self.port_statistics_list = self.get_link_usage_metrics(self.link_filepath)
    
    """
        Return the traffic metrics as a dictionary with the maximum average lambda value as the key and the
        metrics for each simulation as values. 

        @param filepath: traffic file for simulation
        @return list of maximum average lambda values
        @return list of traffic measurements
    """
    def get_traffic_metrics(self, filepath):
        traffic_file = open(filepath)
        max_avg_lambda_list = []
        traffic_measurements = []
        for line in traffic_file:
            traffic_tokens = line.split()
            max_avg_lambda = None
            for token in traffic_tokens:
                traffic_data = token.split(';')
                max_avg_lambda, rest_of_token = self.get_max_avg_lambda(traffic_data[0])
                first_tokens = rest_of_token.split(',')
                tokens = []
                for t in first_tokens:
                    tokens.append(t)
                traffic_measurements.append(tokens)
                modified_tokens = traffic_data[1:]
                for m in modified_tokens:
                    rest_to_add = m.split(',')
                    tokens_ = []
                    for r in rest_to_add:
                        if r == None:
                            continue
                        else:
                            tokens_.append(r)
                    max_avg_lambda_list.append(max_avg_lambda)
                    traffic_measurements.append(tokens_)
        
        traffic_file.close() # Close file once done processing
        traffic_measurements_modified = [x for x in traffic_measurements if x != ['']] # Remove empty lists from list
        
        # Get the time and size distribution parameters
        list_of_traffic_measurements = []
        for traffic_measurement in traffic_measurements_modified:
            length = len(traffic_measurement)
            for i in range(length):
                traffic_dictionary = dict()
                offset = self.create_traffic_time_distribution(traffic_measurements_modified, traffic_dictionary)
                if offset != -1: # Go through this loop if we have a valid offset
                    self.create_traffic_size_distribution(traffic_measurements_modified, offset, traffic_dictionary)
                list_of_traffic_measurements.append(traffic_dictionary)
        
        return max_avg_lambda_list, traffic_measurements_modified

    """
        Fill out dictionary with traffic time distribution metrics and return the offset of where to read size distribution parameters.

        @param traffic_metrics: list of all the flow traffic metrics to be processed
        @param traffic_dictionary: dictionary to fill out with the time distribution information
        @return number of elements read from the list of parameters data
    """
    def create_traffic_time_distribution(self, traffic_metrics, traffic_dictionary):
        if traffic_metrics[0] == 0:
            traffic_dictionary['Time Distribution'] = 'Exponential'
            parameters = dict()
            parameters['Equivalent Lambda'] = data[1]
            parameters['Average Packets Lambda'] = data[2]
            parameters['Exponential Max Factor'] = data[3]
            traffic_dictionary['Time Distribution Parameters'] = parameters
            return 4
        elif traffic_metrics[0] == 1:
            traffic_dictionary['Time Distribution'] = 'Deterministic'
            parameters = dict()
            parameters['Equivalent Lambda'] = data[1]
            parameters['Average Packets Lambda'] = data[2]
            traffic_dictionary['Time Distribution Parameters'] = parameters
            return 3
        elif traffic_metrics[0] == 2:
            traffic_dictionary['Time Distribution'] = 'Uniform'
            parameters = dict()
            parameters['Equivalent Lambda'] = data[1]
            parameters['Min Packet Lambda'] = data[2]
            parameters['Max Packet Lambda'] = data[3]
            traffic_dictionary['Time Distribution Parameters'] = parameters
            return 4
        elif traffic_metrics[0] == 3:
            traffic_dictionary['Time Distribution'] = 'Normal'
            parameters = dict()
            parameters['Equivalent Lambda'] = data[1]
            parameters['Average Packet Lambda'] = data[2]
            parameters['Standard Deviation'] = data[3]
            traffic_dictionary['Time Distribution Parameters'] = parameters
            return 4
        elif traffic_metrics[0] == 4:
            traffic_dictionary['Time Distribution'] = 'OnOff'
            parameters = dict()
            parameters['Equivalent Lambda'] = data[1]
            parameters['Packets Lambda On'] = data[2]
            parameters['Average Time Off'] = data[3]
            parameters['Average Time On'] = data[4]
            parameters['Exponential Max Factor'] = data[5]
            traffic_dictionary['Time Distribution Parameters'] = parameters
            return 6
        elif traffic_metrics[0] == 5:
            traffic_dictionary['Time Distribution'] = 'Normal'
            parameters = dict()
            parameters['Equivalent Lambda'] = data[1]
            parameters['Burst Gen Lambda'] = data[2]
            parameters['Bit Rate'] = data[3]
            parameters['Pare to Min Size'] = data[4]
            parameters['Pare to Max Size'] = data[5]
            parameters['Pare to Alpha'] = data[6]
            parameters['Exponential Max Factor'] = data[7]
            traffic_dictionary['Time Distribution Parameters'] = parameters
            return 8
        else:
            return -1

    """
        Retrieve the size distribution parameters of the traffic data. 

        @param traffic_metrics: list of all the flow traffic metrics to be processed
        @param offset: number of elements read from the list of parameters data
        @param traffic_dictionary: dictionary to fill out with the time distribution information
        @return 0 if successful iteration, or -1 otherwise
    """
    def create_traffic_size_distribution(self, traffic_metrics, offset, traffic_dictionary):
        if traffic_metrics[offset] == 0:
            traffic_dictionary['Size Distribution'] = 'Deterministic'
            parameters = dict{}
            parameters = ['Average Packet Size'] = traffic_metrics[offset + 1]
            traffic_dictionary['Size Distribution Parameters'] = parameters
        elif traffic_metrics[offset] == 1:
            traffic_dictionary['Size Distribution'] = 'Uniform'
            parameters = dict()
            parameters['Average Packet Size'] = traffic_metrics[offset + 1]
            parameters['Min Size'] = traffic_metrics[offset + 2]
            parameters['Max Size'] = traffic_metrics[offset + 3]
            traffic_dictionary['Size Distribution Parameters'] = parameters
        elif traffic_metrics[offset] == 2:
            traffic_dictionary['Size Distribution'] = 'Binomial'
            parameters = dict()
            parameters['Average Packet Size'] = traffic_metrics[offset + 1]
            parameters['Packet Size 1'] = traffic_metrics[offset + 2]
            parameters['Packet Size 2'] = traffic_metrics[offset + 3]
            traffic_dictionary['Size Distribution Parameters'] = parameters
        elif traffic_metrics[offset] == 3:
            traffic_dictionary['Size Distribution'] = 'Generic'
            parameters = dict()
            parameters['Average Packet Size'] = traffic_metrics[offset + 1]
            parameters['Number of Candidates'] = traffic_metrics[offset + 2]
            for i in range(0, int(traffic_metrics[offset + 2]) * 2, 2)
                parameters['Size %d' % (i / 2)] = traffic_metrics[offset + 3 + i]
                parameters['Prob %d' % ( / 2)] = traffic_dictionary[offset + 4 + i]
            traffic_dictionary['Size Distribution Parameters'] = parameters
        else:
            return -1
        return 0
        
    """
        Get the maximum average lambda value and the string without it.

        @param token: original string containing the maximum average lambda value and the rest of the string
        @return maximum average lambda value
        @return rest of string without maximum average lambda value
    """
    def get_max_avg_lambda(self, token):
        bar_index = token.find('|')
        return token[0:bar_index], token[bar_index:].replace('|', '')

    """
        Extract information from the input file containing information about simulation number, graph files, and routing files.
        
        @param filepath: input file path
        @return simulation numbers
        @return list of MatrixPath objects showing routings, if they exist
    """
    def process_input_file(self, filepath):
        input_file = open(filepath)
        sim_numbers = []
        graph_routing_dictionary = dict()
        net_size = filepath.replace('training_data\gnnet-ch21-dataset-train\\', '')[0:2]
        for line in input_file:
            input_data = line.split(';')
            sim_numbers.append(input_data[0])
            filepath_stem = 'training_data\gnnet-ch21-dataset-train\\'
            graph_file = filepath_stem + net_size + '\graphs\\' + input_data[1]
            routing_file = (filepath_stem + net_size + '\\routings\\' + input_data[2]).rstrip()
            graph_routing_dictionary[graph_file] = routing_file
        
        input_file.close() # Close file once done processing

        routing_matrices = []
        # Create routing matrix
        for key in graph_routing_dictionary:
            routing_file = graph_routing_dictionary[key]
            routing_matrix = self.create_routing_matrix(int(net_size), routing_file)
            routing_matrices.append(routing_matrix)
        
        return sim_numbers, routing_matrices 

    """
        Creating a routing object to show an n x n matrix and how each cell [i, j] contains the path to go from node i
        to node j. If 'None' value is present, no route is available. 

        @param net_size: size of topology network
        @param routing_file: file regarding information about routing configuration
        @return MatrixPath object that shows routes between different nodes, if present
    """
    def create_routing_matrix(self, net_size, routing_file):
        MatrixPath = np.empty((net_size, net_size), dtype = object)
        with open(routing_file) as rf:
            for line in rf:
                nodes = line.split(';')
                nodes = list(map(int, nodes))
                MatrixPath[nodes[0], nodes[-1]] = nodes
        return MatrixPath

    """
        Create and return a graph readable structure for a specified GML markup.

        @param filepath: GML markup file path
        @return graph structure
    """
    def graph_process(self, filepath):
        G = networkx.read_gml(filepath, destringizer = int)
        return G
    
    """
        Given a simulation metrics file, extract information about the global packets, global losses, global delays, and
        the metrics list for each instance. 

        @param filepath: simulation file of network topology
        @return list of global packets measurements
        @return list of global losses measurements
        @return list of global delay measurements
        @return list of dictionaries of metrics (performance matrix)
    """
    def get_simulation_metrics(self, filepath):
        sim_file = open(filepath)
        global_packets_list = []
        global_losses_list = []
        global_delay_list = []
        metrics_list = []
        for line in sim_file:
            measurement = line.split()
            measurement_tokens = measurement[0].split(',')
            global_packets = measurement_tokens[0] # Get global packets value
            global_packets_list.append(global_packets)
            measurement_tokens.remove(global_packets) # Remove value once finished
            global_losses = measurement_tokens[1] # Get global losses value
            global_losses_list.append(global_losses)
            measurement_tokens.remove(global_losses) # Remove value once finished
            global_delay_temp = measurement_tokens[2] # Get global delay value and modify
            bar_index = global_delay_temp.find('|')
            global_delay = global_delay_temp[0:bar_index]
            global_delay_list.append(global_delay)

            metrics_list_ = self.get_traffic_measurementss(global_delay, measurement_tokens) # Get the rest of the list metrics
            metrics_list.append(metrics_list_)
        
        sim_file.close() # Close the file once done processing
        return global_packets_list, global_losses_list, global_delay_list, metrics_list

    """
        Extracting the individual list metrics and appending them all to one array. 

        @param global_delay: used to remove before iterating through the measurement tokens
        @param measurement_tokens: array of metrics that are separated by '|' and ';'
        @return list of dictionaries of metrics
    """
    def get_traffic_measurementss(self, global_delay, measurement_tokens):
        metrics_list = []
        modified_measurements = self.modify_tokens(measurement_tokens)  
        if global_delay in modified_measurements:
            modified_measurements.remove(global_delay)  
        # Get the rest of the simulation tokens
        counter = 0
        while (counter < len(modified_measurements)):
            metric_aggregated_dictionary = dict() # Re-initialize dictionary to hold the metrics
            for i in range(0, 11, len(modified_measurements)):
                # Bandwidth
                bandwidth = modified_measurements[i]
                metric_aggregated_dictionary['Average Bandwidth'] = bandwidth
                # Number of packets transmitted
                number_packets_transmitted = modified_measurements[i + 1]
                metric_aggregated_dictionary['Packets Transmitted'] = number_packets_transmitted
                # Number of packets dropped
                number_packets_dropped = modified_measurements[i + 2]
                metric_aggregated_dictionary['Packets Dropped'] = number_packets_dropped 
                # Average per-packet delay
                avg_delay = modified_measurements[i + 3]
                metric_aggregated_dictionary['Average Per-Packet Delay'] = avg_delay
                # Neperian logarithm of per-packet delay
                neperian_logarithm = modified_measurements[i + 4]
                metric_aggregated_dictionary['Neperian Logarithm'] = neperian_logarithm
                # Percentile 10 of per-packet delay
                percentile_10 = modified_measurements[i + 5]
                metric_aggregated_dictionary['Percentile 10'] = percentile_10 
                # Percentile 20 of per-packet delay
                percentile_20 = modified_measurements[i + 6]
                metric_aggregated_dictionary['Percentile 20'] = percentile_20 
                # Percentile 50 of per-packet delay
                percentile_50 = modified_measurements[i + 7]
                metric_aggregated_dictionary['Percentile 50'] = percentile_50
                # Percentile 80 of per-packet delay
                percentile_80 = modified_measurements[i + 8]
                metric_aggregated_dictionary['Percentile 80'] = percentile_80 
                # Percentile 90 of per-packet delay
                percentile_90 = modified_measurements[i + 9]
                metric_aggregated_dictionary['Percentile 90'] = percentile_90 
                # Variance of per-packet delay (jitter)
                variance_delay = modified_measurements[i + 10]
                metric_aggregated_dictionary['Jitter'] = variance_delay
            
            counter = counter + 1 # Increment counter
            metrics_list.append(metric_aggregated_dictionary) # Append to master list of metrics

        return metrics_list

    """
        Modify the measurement tokens list so that are no '|' or ';' present, but all tokens are separated and present. 

        @param measurement_tokens: array of metrics that are separated by '|' and ';'
        @return modified list in which each token is present in the list
    """
    def modify_tokens(self, measurement_tokens):
        modified_measurements = []
        # Modify measurements so they can be read and organized
        for token in measurement_tokens:
            if '|' in token:
                new_token = token.split('|')
                for t in new_token:
                    modified_measurements.append(t)
            elif ';' in token:
                new_token = token.split(';')
                for t in new_token:
                    modified_measurements.append(t)
            else:
                modified_measurements.append(token)
        return modified_measurements
    """
        Given a link usage file, extract information about various metrics present. If a link does not exist, populate the 
        list of metrics with all -1. 

        @param filepath: link usage file of source-destination pair
        @return list of port statistics by each measure
    """
    def get_link_usage_metrics(self, filepath):
        link_file = open(filepath)
        port_statistics_list = []
        for line in link_file:
            port_statistics = line.split(';')
            for token in port_statistics:
                port_statistics_individual = []
                if token == '-1':
                    # Link does not exist
                    link_exists = False
                    port_statistics_individual.append(link_exists)
                    for i in range(8):
                        port_statistics_individual.append(-1)
                    port_statistics_list.append(port_statistics_individual)
                elif token == '\n': # Go to next line at end of line
                    break
                else:
                    tokens = token.split(',')
                    # The link exists
                    link_exists = True
                    port_statistics_individual.append(link_exists)
                    # Average utilization of the outgoing port
                    avg_utilization = tokens[0]
                    port_statistics_individual.append(avg_utilization)
                    # Average packet loss rate in the outgoing port
                    avg_packet_loss = tokens[1]
                    port_statistics_individual.append(avg_packet_loss)
                    # Average packet length of the packets transmitted through the outgoing port
                    avg_packet_length = tokens[2]
                    port_statistics_individual.append(avg_packet_length)
                    # Average utilization of the first queue of the outgoing port
                    avg_utilization_first = tokens[3]
                    port_statistics_individual.append(avg_utilization_first)
                    # Average packet loss rate in the first queue of the outgoing port
                    avg_packet_loss_rate = tokens[4]
                    port_statistics_individual.append(avg_packet_loss_rate)
                    # Average port occupancy (service and waiting queue) of the first queue of the outgoing port
                    avg_port_occupancy = tokens[5]
                    port_statistics_individual.append(avg_port_occupancy)
                    # Maximum queue occupancy of the first queue of the outgoing port
                    max_queue_occupancy = tokens[6]
                    port_statistics_individual.append(max_queue_occupancy)
                    # Average packet length of the packets transmitted through the first queue of the outgoing port
                    avg_packet_length_first = tokens[7]
                    port_statistics_individual.append(avg_packet_length_first)
                    port_statistics_list.append(port_statistics_individual)

        link_file.close() # Close the file once done processing
        return port_statistics_list

"""
    Extract contents of tar files downloaded.

    @param filename: path and name of the tar file (.tar)
    @param path: where data should be located
"""
def extract(filename, path):
    if filename.endswith("tar.gz"):
        tar = tarfile.open(filename, "r:gz")
        tar.extractall(path = path)
        print("Path 1: " + filename + " unzipped.")
        tar.close()
        return
    elif filename.endswith("tar"):
        tar = tarfile.open(filename, "r:")
        tar.extractall(path = path)
        print("Path 2: " + filename + " unzipped.")
        tar.close()
        return
    else:
        print("Not a tar file.")
        return

"""
    Within a directory, extract all the contents within all the tar files in that directory. 
    Print the progress of the extraction.

    @param main_filepath: file path that contains all the tar files
"""
def extract_all_in_filepath(main_filepath):
    files = os.listdir(main_filepath)
    files_length = len(files)
    extraction_progress = 0
    for tar_file in os.listdir(main_filepath):
        if tar_file.endswith('.gz'): # Tar files only 
            # All the names end with 'tar.gz' in this path
            new_directory_path = main_filepath + tar_file.replace('tar.gz', '')
            os.mkdir(new_directory_path)
            extract(main_filepath + tar_file, new_directory_path)
            extraction_progress = extraction_progress + 1
            print("Unzipped " + str(extraction_progress) + " out of " + str(files_length) + " files.")

# Driver code
INPUT_FILE = 'training_data\gnnet-ch21-dataset-train\\25\\results_25_400-2000_0_24\\results_25_400-2000_0_24\input_files.txt'
TRAFFIC_FILE = 'training_data\gnnet-ch21-dataset-train\\25\\results_25_400-2000_0_24\\results_25_400-2000_0_24\\traffic.txt'
LINK_FILE = 'training_data\gnnet-ch21-dataset-train\\25\\results_25_400-2000_0_24\\results_25_400-2000_0_24\linkUsage.txt'
SIM_FILE = 'training_data\gnnet-ch21-dataset-train\\25\\results_25_400-2000_0_24\\results_25_400-2000_0_24\simulationResults.txt'
dataset = NetworkInput(INPUT_FILE, TRAFFIC_FILE, LINK_FILE, SIM_FILE)