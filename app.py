import os
import uuid
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 連番ファイル名を作る関数 (同名ファイルがあれば (1),(2) など)
def find_unique_filename(base_path):
    if not os.path.exists(base_path):
        return base_path
    base, ext = os.path.splitext(base_path)
    i = 1
    while True:
        new_path = f"{base}({i}){ext}"
        if not os.path.exists(new_path):
            return new_path
        i += 1

# 512->384変換 (青/赤を回転、灰捨て)
def rearrange_512_to_384(cropped_512x256):
    new_img = np.zeros((256,384,3), dtype=np.uint8)

    # Yellow
    yellow = cropped_512x256[0:128, 0:384]
    new_img[0:128, 0:384] = yellow

    # Blue
    blue = cropped_512x256[64:128, 384:512]
    blue_rot = cv2.rotate(blue, cv2.ROTATE_90_CLOCKWISE)
    new_img[128:256, 0:64] = blue_rot

    # Red
    red = cropped_512x256[0:64, 384:512]
    red_rot = cv2.rotate(red, cv2.ROTATE_90_CLOCKWISE)
    new_img[128:256, 64:128] = red_rot

    # Green
    green = cropped_512x256[128:256, 128:384]
    new_img[128:256, 128:384] = green

    return new_img

@app.route('/')
def index():
    return render_template('index.html')  # templates/index.html

@app.route('/upload', methods=['POST'])
def upload():
    """
    動画をアップロードして保存。
    """
    file = request.files.get('video')
    if not file:
        return jsonify({"error":"No file"}), 400

    filename = secure_filename(file.filename)
    unique_id = str(uuid.uuid4())
    save_name = unique_id + "_" + filename
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], save_name)
    file.save(save_path)

    # 動画情報を取得して返す
    cap = cv2.VideoCapture(save_path)
    if not cap.isOpened():
        return jsonify({"error":"動画を開けません"}), 400
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    if fps<=0: fps=30
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    if width<512 or height<256:
        return jsonify({"error":"512×256未満です"}),400

    return jsonify({
        "file_id": save_name,
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": frame_count
    })

@app.route('/frame', methods=['GET'])
def get_frame():
    """
    ?file_id=xxx & frame_index=N で N番目フレームを PNG で返す
    """
    file_id = request.args.get("file_id")
    frame_index = int(request.args.get("frame_index",0))
    path = os.path.join(app.config['UPLOAD_FOLDER'], file_id)

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return "Cannot open video", 400
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return "Frame not found", 400

    ret, buf = cv2.imencode(".png", frame)
    if not ret:
        return "Fail to encode", 500
    return buf.tobytes(), 200, {'Content-Type':'image/png'}

@app.route('/transform', methods=['POST'])
def transform():
    """
    JSON {file_id, crop_x, crop_y, crop_w, crop_h} を受け取り、
    1) その範囲を切り出し
    2) 512x256にリサイズ
    3) rearrange_512_to_384
    4) 384x256を出力
    """
    data = request.json
    file_id = data.get('file_id')
    cx = data.get('crop_x')
    cy = data.get('crop_y')
    cw = data.get('crop_w')
    ch = data.get('crop_h')

    in_path = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
    out_name = find_unique_filename(os.path.splitext(in_path)[0] + "_converted.mp4")
    cap = cv2.VideoCapture(in_path)
    if not cap.isOpened():
        return jsonify({"error":"Cannot open video"}),400

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps<=0: fps=30

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(out_name, fourcc, fps, (384,256))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        sub_region = frame[cy:cy+ch, cx:cx+cw]
        resized_512x256 = cv2.resize(sub_region, (512,256))
        out_frame = rearrange_512_to_384(resized_512x256)
        writer.write(out_frame)

    writer.release()
    cap.release()

    # 成功 → out_name を返す
    out_file = os.path.basename(out_name)  # "xxx_converted.mp4"
    return jsonify({"out_file": out_file})

@app.route('/download/<out_file>', methods=['GET'])
def download(out_file):
    """生成された動画をダウンロードさせる"""
    path = os.path.join(app.config['UPLOAD_FOLDER'], out_file)
    if not os.path.exists(path):
        return "Not found", 404
    return send_file(path, as_attachment=True, download_name="converted.mp4")

if __name__ == "__main__":
    app.run(debug=True)
