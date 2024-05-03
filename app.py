import json
import heapq
import datetime
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

with open('data/deliverydata.json') as f:
    deliveries = json.load(f)
with open('data/traffic_data.json') as f:
    traffic_data = json.load(f)


def get_traffic_multiplier(start, destination, traffic_data):
    for data in traffic_data['traffic_info']:
        if data['start'] == start and data['destination'] == destination:
            return data['congestion_level']
    return 0 


def prepare_delivery_route_map(traffic_data):
    graph = {'Warehouse': {}}
    for delivery in deliveries:
        start = delivery['StartPoint']
        destination = delivery['Destination']
        congestion_level = get_traffic_multiplier(start, destination, traffic_data)
        distance = delivery['Distance'] * (1 + congestion_level)
        graph.setdefault(start, {})[destination] = distance
        graph.setdefault(destination, {})['Warehouse'] = distance
    return graph

def calculate_routes(graph, start_vertex):
    distances = {vertex: float('inf') for vertex in graph}
    distances[start_vertex] = 0
    priority_queue = [(0, start_vertex)]
    
    while priority_queue:
        current_distance, current_vertex = heapq.heappop(priority_queue)
        if current_distance > distances[current_vertex]:
            continue
        for neighbour, weight in graph[current_vertex].items():
            new_distance = current_distance + weight
            if new_distance < distances[neighbour]:
                distances[neighbour] = new_distance
                heapq.heappush(priority_queue, (new_distance, neighbour))
    return distances

def format_route_results(route_results):
    formatted_results = []
    current_time = datetime.datetime.now() 
    previous_unloading_time = 0 

    for i, delivery in enumerate(deliveries):
        start_point = delivery.get('StartPoint', 'Unknown Start')
        destination = delivery.get('Destination', 'Unknown Destination')
        distance = route_results.get(destination, 0)
        congestion_level = get_traffic_multiplier(start_point, destination, traffic_data)
        adjusted_distance = distance * (1 + congestion_level)
        travel_time = (adjusted_distance / 50) * 60 
        item_weight = delivery.get('ItemWeight', 0)
        unloading_time = max(5, (item_weight // 100) * 5)  

        expected_time = current_time + datetime.timedelta(minutes=travel_time)
        expected_time += datetime.timedelta(minutes=previous_unloading_time)  
        estimated_arrival = expected_time.strftime('%Y-%m-%d %H:%M')  

        scheduled_window = f"{delivery['DeliveryStart']} - {delivery['DeliveryEnd']}"

        formatted_results.append({
            "order": i + 1,
            "start": start_point,
            "destination": destination,
            "distance": f"{adjusted_distance:.2f} km",
            "travel_time": f"{int(travel_time)} mins",
            "estimated_arrival": estimated_arrival,  
            "unloading_time": f"{unloading_time} mins",
            "item_weight": f"{item_weight} kg",
            "scheduled_window": scheduled_window,
            "contact": delivery.get('ContactName', 'No contact'),
            "items": delivery.get('Items', 'No items specified'),
            "special_instructions": delivery.get('SpecialInstructions', 'None')
        })

        previous_unloading_time = unloading_time 
        current_time = expected_time 

    return formatted_results


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/calculate-route', methods=['GET'])
def calculate_route():
    global traffic_data  
    new_traffic_data = request.args.get('traffic_data')  
    if new_traffic_data:
        traffic_data = json.loads(new_traffic_data)  
    delivery_map = prepare_delivery_route_map(traffic_data)  
    route_results = calculate_routes(delivery_map, 'Warehouse')
    formatted_results = format_route_results(route_results)
    return jsonify(formatted_results)

if __name__ == '__main__':
    app.run(debug=True)
