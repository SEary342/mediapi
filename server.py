from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# This is a placeholder for the player control.
# In a real application, you would import and use your player object here.
player_control = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/playback/play', methods=['POST'])
def play():
    if player_control:
        player_control.play()
    return jsonify({'status': 'playing'})

@app.route('/api/playback/pause', methods=['POST'])
def pause():
    if player_control:
        player_control.pause()
    return jsonify({'status': 'paused'})

@app.route('/api/playback/next', methods=['POST'])
def next_track():
    if player_control:
        player_control.next()
    return jsonify({'status': 'next'})

@app.route('/api/playback/previous', methods=['POST'])
def previous_track():
    if player_control:
        player_control.previous()
    return jsonify({'status': 'previous'})

@app.route('/api/sources', methods=['GET'])
def get_sources():
    if player_control:
        return jsonify(player_control.menu_options)
    return jsonify([])

@app.route('/api/select_source', methods=['POST'])
def select_source():
    source = request.json.get('source')
    if player_control and source:
        if "Jellyfin" in source:
            player_control.load_jellyfin()
        elif "Audiobook" in source:
            player_control.load_abs()
        elif "Local Files" in source:
            player_control.load_local(shuffle=False)
        elif "Shuffle" in source:
            player_control.load_local(shuffle=True)
        elif "Bluetooth" in source:
            player_control.scan_bluetooth()
        return jsonify({'status': 'source_selected', 'source': source})
    return jsonify({'status': 'error', 'message': 'player not ready or no source provided'}), 400

@app.route('/api/playlist', methods=['GET'])
def get_playlist():
    if player_control:
        return jsonify([item['name'] for item in player_control.playlist])
    return jsonify([])

@app.route('/api/play_item/<int:index>', methods=['POST'])
def play_item(index):
    if player_control:
        player_control.play_selection(index)
        return jsonify({'status': 'playing_item', 'index': index})
    return jsonify({'status': 'error', 'message': 'player not ready'}), 400

@app.route('/api/bt/scan', methods=['POST'])
def scan_bluetooth():
    if player_control:
        player_control.scan_bluetooth()
        return jsonify({'status': 'scanning'})
    return jsonify({'status': 'error', 'message': 'player not ready'}), 400

@app.route('/api/bt/devices', methods=['GET'])
def get_bt_devices():
    if player_control:
        return jsonify([device['name'] for device in player_control.bt_devices])
    return jsonify([])

@app.route('/api/bt/connect/<int:index>', methods=['POST'])
def connect_bluetooth(index):
    if player_control:
        player_control.connect_bluetooth(index)
        return jsonify({'status': 'connecting_bt', 'index': index})
    return jsonify({'status': 'error', 'message': 'player not ready'}), 400

@app.route('/api/status', methods=['GET'])
def get_status():
    if player_control:
        status = {
            'view_state': player_control.view_state,
            'current_track': player_control.playlist[player_control.current_index]['name'] if player_control.view_state == 'PLAYING' and player_control.playlist else None,
            'playlist_length': len(player_control.playlist)
        }
        return jsonify(status)
    return jsonify({'view_state': 'UNAVAILABLE'})


def run_server(player):
    global player_control
    player_control = player
    app.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    # This is for testing the server independently.
    run_server(None)
