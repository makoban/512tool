window.addEventListener("DOMContentLoaded", () => {
  const uploadForm = document.getElementById("uploadForm");
  const infoArea = document.getElementById("infoArea");
  const videoFrame = document.getElementById("videoFrame");
  const frameIndexInput = document.getElementById("frameIndex");
  const showFrameBtn = document.getElementById("showFrameBtn");
  const transformBtn = document.getElementById("transformBtn");
  const downloadLink = document.getElementById("downloadLink");
  const cropXInput = document.getElementById("cropX");
  const cropYInput = document.getElementById("cropY");
  const cropWInput = document.getElementById("cropW");
  const cropHInput = document.getElementById("cropH");

  let currentFileId = null;
  let videoWidth = 0;
  let videoHeight = 0;
  let frameCount = 0;

  // 1) 動画アップロード
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(uploadForm);
    try {
      const res = await fetch("/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.error) {
        alert("アップロード失敗: " + data.error);
        return;
      }
      currentFileId = data.file_id;
      videoWidth = data.width;
      videoHeight = data.height;
      frameCount = data.frame_count;

      infoArea.textContent =
        `動画ID: ${currentFileId}, ` +
        `解像度: ${videoWidth}x${videoHeight}, frames=${frameCount}`;
      alert("アップロード完了。フレーム番号を指定→表示でプレビューできます。");
    } catch (err) {
      alert("アップロードエラー: " + err);
    }
  });

  // 2) フレーム表示
  showFrameBtn.addEventListener("click", async () => {
    if (!currentFileId) {
      alert("動画を先にアップロードしてください。");
      return;
    }
    const idx = parseInt(frameIndexInput.value) || 0;
    const url = `/frame?file_id=${currentFileId}&frame_index=${idx}`;
    // <img> のsrcにセット
    videoFrame.src = url;
  });

  // 3) トリミング開始
  transformBtn.addEventListener("click", async () => {
    if (!currentFileId) {
      alert("ファイルがありません。");
      return;
    }
    const cx = parseInt(cropXInput.value) || 0;
    const cy = parseInt(cropYInput.value) || 0;
    const cw = parseInt(cropWInput.value) || 512;
    const ch = parseInt(cropHInput.value) || 256;

    const bodyData = {
      file_id: currentFileId,
      crop_x: cx,
      crop_y: cy,
      crop_w: cw,
      crop_h: ch,
    };
    try {
      const res = await fetch("/transform", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyData),
      });
      const data = await res.json();
      if (data.error) {
        alert("変換失敗: " + data.error);
        return;
      }
      // 変換後ファイル名
      const outFile = data.out_file;
      // ダウンロードリンク生成
      const dlUrl = `/download/${outFile}`;
      downloadLink.innerHTML = `<a href="${dlUrl}" target="_blank">変換後をダウンロード</a>`;
    } catch (err) {
      alert("変換エラー: " + err);
    }
  });

  // --- もしドラッグ操作で可変枠を描くなら
  //   <canvas>を使って mousedown/mousemove/mouseup で (cropX,cropY,cropW,cropH)
  //   を計算 → cropXInput.value=..., などに反映
});
