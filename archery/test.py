from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
import time

params = BrainFlowInputParams()
params.serial_port = 'COM3'  # ← ここは表示されてたCOM番号に合わせる（COM3ならそのままでOK）

print("creating board...")
board = BoardShim(BoardIds.GANGLION_BOARD.value, params)

print("preparing session...")
board.prepare_session()

print("starting stream...")
board.start_stream()

time.sleep(3)

print("getting data...")
data = board.get_current_board_data(200)
print("data shape:", data.shape)
print(data)

board.stop_stream()
board.release_session()