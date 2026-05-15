<?php
declare(strict_types=1);
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FaceAssist QR Registration Consent</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7f9;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #5f6c7b;
      --border: #d8dee7;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --danger: #b42318;
      --ok: #067647;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }
    main {
      width: min(920px, calc(100% - 24px));
      margin: 0 auto;
      padding: 20px 0 28px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 28px;
      line-height: 1.2;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 18px;
    }
    p { margin: 0 0 14px; }
    .muted { color: var(--muted); }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: clamp(16px, 4vw, 20px);
      margin-top: 14px;
    }
    label {
      display: block;
      font-weight: 700;
      margin-bottom: 6px;
    }
    input[type="text"] {
      width: 100%;
      max-width: 520px;
      padding: 12px 14px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 18px;
    }
    .check {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      margin-top: 16px;
      font-weight: 400;
    }
    .check input {
      margin-top: 5px;
      transform: scale(1.15);
    }
    button, .button {
      display: inline-block;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      padding: 13px 16px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
    }
    button:hover, .button:hover { background: var(--accent-dark); }
    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    ul { margin: 8px 0 0 20px; padding: 0; }
    li { margin: 6px 0; }
    .status {
      margin-top: 14px;
      padding: 12px 14px;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: #f8fafc;
    }
    .status.error {
      border-color: #f0b4ae;
      background: #fff5f3;
      color: var(--danger);
    }
    .status.ok {
      border-color: #a7d8bd;
      background: #f0fdf4;
      color: var(--ok);
    }
    .qr-result {
      display: none;
      grid-template-columns: minmax(220px, 390px) 1fr;
      gap: 18px;
      align-items: start;
    }
    .qr-result.is-visible { display: grid; }
    .is-hidden { display: none !important; }
    .qr-frame {
      display: flex;
      justify-content: center;
    }
    #qrCanvas {
      width: 100%;
      max-width: min(390px, calc(100vw - 56px));
      height: auto;
      background: #fff;
      border: 10px solid #fff;
      box-shadow: 0 8px 24px rgba(23, 32, 42, 0.12);
      image-rendering: pixelated;
    }
    .instruction-list {
      margin-top: 8px;
    }
    code {
      background: #eef2f6;
      padding: 2px 5px;
      border-radius: 4px;
      overflow-wrap: anywhere;
    }
    @media (max-width: 760px) {
      main {
        width: min(100% - 18px, 920px);
        padding-top: 10px;
      }
      .qr-result {
        grid-template-columns: 1fr;
        gap: 14px;
      }
      h1 { font-size: 24px; }
      #qrCanvas {
        max-width: calc(100vw - 42px);
      }
    }
  </style>
</head>
<body>
<main>
  <h1>FaceAssist QR Registration</h1>
  <p class="muted">Create a QR code for local face registration on the FaceAssist system.</p>

  <section id="qrResult" class="panel qr-result">
    <div class="qr-frame">
      <canvas id="qrCanvas" width="390" height="390" aria-label="Generated QR code"></canvas>
    </div>
    <div>
      <h2>Show this QR code to FaceAssist</h2>
      <p>Hold your phone screen in front of the FaceAssist camera until the device reads the code.</p>
      <ul class="instruction-list">
        <li>Keep the QR code large and bright on your screen.</li>
        <li>After FaceAssist speaks your name, stand in the doorway and look toward the camera.</li>
        <li>Wait while FaceAssist counts down and takes the registration photos.</li>
      </ul>
      <p><strong>Name in QR:</strong> <span id="payloadLabel"></span></p>
      <p><strong>Local storage name:</strong> <code id="storageLabel"></code></p>
      <p><a id="downloadLink" class="button" href="#" download="faceassist-registration-qr.png">Download PNG</a></p>
    </div>
  </section>

  <section id="registrationPanel" class="panel">
    <form id="qrForm" action="javascript:void(0)" novalidate>
      <label for="name">Your name</label>
      <input id="name" name="name" type="text" autocomplete="name" maxlength="80" required>
      <p class="muted">This name will be encoded into the QR code. The local FaceAssist system may convert spaces and special characters to underscores for filenames.</p>

      <h2>Consent and privacy notice</h2>
      <ul>
        <li>I agree to be registered and recognised by the FaceAssist face recognition system.</li>
        <li>I understand that FaceAssist is built to help blind people know when somebody is at their door.</li>
        <li>I understand that the FaceAssist device runs completely locally without an internet connection.</li>
        <li>I understand that the AI-based face recognition runs locally on the FaceAssist device.</li>
        <li>I understand that, after this QR code is scanned by the local device, FaceAssist may store local face photos and face embeddings for recognition.</li>
        <li>I understand that local files may be stored on the FaceAssist device under <code>faceassist/known/</code>, including a folder with photos and a <code>.npz</code> recognition file.</li>
        <li>This page generates the QR code in my browser. My entered name is not submitted by this form to the webserver.</li>
        <li>No face photos or face embeddings are collected by this web page.</li>
        <li>No data is intentionally sent to external parties by this QR generation page.</li>
        <li>I can ask the FaceAssist system operator to delete my local registration data.</li>
        <li>I understand that automated recognition may be inaccurate in some circumstances.</li>
      </ul>

      <label class="check">
        <input id="consent" type="checkbox" name="consent" value="yes" required>
        <span>I have read the notice above and give consent for local registration and recognition.</span>
      </label>

      <p style="margin-top:18px;">
        <button type="submit">Create QR code</button>
      </p>

      <div id="status" class="status" aria-live="polite">Enter your name, read the notice, and tick the consent box.</div>
    </form>
  </section>

  <section id="operatorNote" class="panel">
    <h2>Operator note</h2>
    <p class="muted">This is a technical consent screen, not legal advice. The FaceAssist operator remains responsible for privacy notices, lawful basis or consent records, retention, access control, deletion requests, and local legal requirements.</p>
  </section>
</main>

<script>
(() => {
  "use strict";

  const QR_INFO = [
    null,
    {data: 16, ec: 10, blocks: [[1, 16]], align: []},
    {data: 28, ec: 16, blocks: [[1, 28]], align: [6, 18]},
    {data: 44, ec: 26, blocks: [[1, 44]], align: [6, 22]},
    {data: 64, ec: 18, blocks: [[2, 32]], align: [6, 26]},
    {data: 86, ec: 24, blocks: [[2, 43]], align: [6, 30]},
    {data: 108, ec: 16, blocks: [[4, 27]], align: [6, 34]},
    {data: 124, ec: 18, blocks: [[4, 31]], align: [6, 22, 38]},
    {data: 154, ec: 22, blocks: [[2, 38], [2, 39]], align: [6, 24, 42]},
    {data: 182, ec: 22, blocks: [[3, 36], [2, 37]], align: [6, 26, 46]},
    {data: 216, ec: 26, blocks: [[4, 43], [1, 44]], align: [6, 28, 50]}
  ];
  const REMAINDER_BITS = [0, 0, 7, 7, 7, 7, 7, 0, 0, 0, 0];
  const textEncoder = new TextEncoder();
  const EXP = new Array(512);
  const LOG = new Array(256);

  let x = 1;
  for (let i = 0; i < 255; i++) {
    EXP[i] = x;
    LOG[x] = i;
    x <<= 1;
    if (x & 0x100) {
      x ^= 0x11D;
    }
  }
  for (let i = 255; i < 512; i++) {
    EXP[i] = EXP[i - 255];
  }

  function gfMul(a, b) {
    return a === 0 || b === 0 ? 0 : EXP[LOG[a] + LOG[b]];
  }

  function rsGenerator(degree) {
    let poly = [1];
    for (let i = 0; i < degree; i++) {
      const next = new Array(poly.length + 1).fill(0);
      for (let j = 0; j < poly.length; j++) {
        next[j] ^= poly[j];
        next[j + 1] ^= gfMul(poly[j], EXP[i]);
      }
      poly = next;
    }
    return poly;
  }

  function rsRemainder(data, degree) {
    const gen = rsGenerator(degree);
    const rem = new Array(degree).fill(0);
    for (const b of data) {
      const factor = b ^ rem.shift();
      rem.push(0);
      for (let i = 0; i < degree; i++) {
        rem[i] ^= gfMul(gen[i + 1], factor);
      }
    }
    return rem;
  }

  function bitBuffer() {
    const bits = [];
    return {
      bits,
      append(value, length) {
        for (let i = length - 1; i >= 0; i--) {
          bits.push(((value >>> i) & 1) !== 0);
        }
      }
    };
  }

  function chooseVersion(bytes) {
    for (let version = 1; version < QR_INFO.length; version++) {
      const countBits = version < 10 ? 8 : 16;
      const neededBits = 4 + countBits + bytes.length * 8;
      if (neededBits <= QR_INFO[version].data * 8) {
        return version;
      }
    }
    throw new Error("Name is too long for this standalone QR generator.");
  }

  function makeDataCodewords(bytes, version) {
    const info = QR_INFO[version];
    const countBits = version < 10 ? 8 : 16;
    const bb = bitBuffer();
    bb.append(0x4, 4);
    bb.append(bytes.length, countBits);
    for (const b of bytes) {
      bb.append(b, 8);
    }

    const capacity = info.data * 8;
    const terminator = Math.min(4, capacity - bb.bits.length);
    bb.append(0, terminator);
    while (bb.bits.length % 8 !== 0) {
      bb.bits.push(false);
    }

    const codewords = [];
    for (let i = 0; i < bb.bits.length; i += 8) {
      let b = 0;
      for (let j = 0; j < 8; j++) {
        b = (b << 1) | (bb.bits[i + j] ? 1 : 0);
      }
      codewords.push(b);
    }

    for (let pad = 0; codewords.length < info.data; pad++) {
      codewords.push(pad % 2 === 0 ? 0xEC : 0x11);
    }
    return codewords;
  }

  function addErrorCorrection(data, version) {
    const info = QR_INFO[version];
    const dataBlocks = [];
    const ecBlocks = [];
    let offset = 0;

    for (const [count, size] of info.blocks) {
      for (let i = 0; i < count; i++) {
        const block = data.slice(offset, offset + size);
        offset += size;
        dataBlocks.push(block);
        ecBlocks.push(rsRemainder(block, info.ec));
      }
    }

    const result = [];
    const maxData = Math.max(...dataBlocks.map(block => block.length));
    for (let i = 0; i < maxData; i++) {
      for (const block of dataBlocks) {
        if (i < block.length) {
          result.push(block[i]);
        }
      }
    }

    for (let i = 0; i < info.ec; i++) {
      for (const block of ecBlocks) {
        result.push(block[i]);
      }
    }
    return result;
  }

  function newMatrix(size) {
    return Array.from({length: size}, () => new Array(size).fill(false));
  }

  function cloneMatrix(matrix) {
    return matrix.map(row => row.slice());
  }

  function setModule(matrix, reserved, x, y, dark, isFunction = true) {
    if (x < 0 || y < 0 || y >= matrix.length || x >= matrix.length) {
      return;
    }
    matrix[y][x] = !!dark;
    if (isFunction) {
      reserved[y][x] = true;
    }
  }

  function drawFinder(matrix, reserved, x, y) {
    for (let dy = -1; dy <= 7; dy++) {
      for (let dx = -1; dx <= 7; dx++) {
        const xx = x + dx;
        const yy = y + dy;
        const dark = dx >= 0 && dx <= 6 && dy >= 0 && dy <= 6
          && (dx === 0 || dx === 6 || dy === 0 || dy === 6 || (dx >= 2 && dx <= 4 && dy >= 2 && dy <= 4));
        setModule(matrix, reserved, xx, yy, dark, true);
      }
    }
  }

  function drawAlignment(matrix, reserved, cx, cy) {
    for (let dy = -2; dy <= 2; dy++) {
      for (let dx = -2; dx <= 2; dx++) {
        const dist = Math.max(Math.abs(dx), Math.abs(dy));
        setModule(matrix, reserved, cx + dx, cy + dy, dist !== 1, true);
      }
    }
  }

  function drawFunctionPatterns(matrix, reserved, version) {
    const size = matrix.length;
    drawFinder(matrix, reserved, 0, 0);
    drawFinder(matrix, reserved, size - 7, 0);
    drawFinder(matrix, reserved, 0, size - 7);

    for (let i = 8; i <= size - 9; i++) {
      const dark = i % 2 === 0;
      setModule(matrix, reserved, i, 6, dark, true);
      setModule(matrix, reserved, 6, i, dark, true);
    }

    const align = QR_INFO[version].align;
    for (const cy of align) {
      for (const cx of align) {
        const overlapsFinder =
          (cx <= 8 && cy <= 8) ||
          (cx >= size - 9 && cy <= 8) ||
          (cx <= 8 && cy >= size - 9);
        if (!overlapsFinder) {
          drawAlignment(matrix, reserved, cx, cy);
        }
      }
    }

    reserveFormat(matrix, reserved);
    setModule(matrix, reserved, 8, size - 8, true, true);

    if (version >= 7) {
      drawVersion(matrix, reserved, version);
    }
  }

  function reserveFormat(matrix, reserved) {
    const size = matrix.length;
    for (let i = 0; i <= 5; i++) {
      setModule(matrix, reserved, 8, i, false, true);
    }
    setModule(matrix, reserved, 8, 7, false, true);
    setModule(matrix, reserved, 8, 8, false, true);
    setModule(matrix, reserved, 7, 8, false, true);
    for (let i = 9; i < 15; i++) {
      setModule(matrix, reserved, 14 - i, 8, false, true);
    }
    for (let i = 0; i < 8; i++) {
      setModule(matrix, reserved, size - 1 - i, 8, false, true);
    }
    for (let i = 8; i < 15; i++) {
      setModule(matrix, reserved, 8, size - 15 + i, false, true);
    }
  }

  function bchRemainder(value, polynomial, degree) {
    value <<= degree;
    for (let i = Math.floor(Math.log2(value)); i >= degree; i--) {
      if (((value >>> i) & 1) !== 0) {
        value ^= polynomial << (i - degree);
      }
    }
    return value;
  }

  function drawVersion(matrix, reserved, version) {
    const size = matrix.length;
    const bits = (version << 12) | bchRemainder(version, 0x1F25, 12);
    for (let i = 0; i < 18; i++) {
      const dark = ((bits >>> i) & 1) !== 0;
      setModule(matrix, reserved, size - 11 + (i % 3), Math.floor(i / 3), dark, true);
      setModule(matrix, reserved, Math.floor(i / 3), size - 11 + (i % 3), dark, true);
    }
  }

  function formatBits(mask) {
    const data = mask; // Error correction level M uses format bits 00.
    return ((data << 10) | bchRemainder(data, 0x537, 10)) ^ 0x5412;
  }

  function drawFormat(matrix, mask) {
    const size = matrix.length;
    const bits = formatBits(mask);
    for (let i = 0; i <= 5; i++) {
      matrix[i][8] = ((bits >>> i) & 1) !== 0;
    }
    matrix[7][8] = ((bits >>> 6) & 1) !== 0;
    matrix[8][8] = ((bits >>> 7) & 1) !== 0;
    matrix[8][7] = ((bits >>> 8) & 1) !== 0;
    for (let i = 9; i < 15; i++) {
      matrix[8][14 - i] = ((bits >>> i) & 1) !== 0;
    }
    for (let i = 0; i < 8; i++) {
      matrix[8][size - 1 - i] = ((bits >>> i) & 1) !== 0;
    }
    for (let i = 8; i < 15; i++) {
      matrix[size - 15 + i][8] = ((bits >>> i) & 1) !== 0;
    }
    matrix[size - 8][8] = true;
  }

  function maskBit(mask, x, y) {
    switch (mask) {
      case 0: return (x + y) % 2 === 0;
      case 1: return y % 2 === 0;
      case 2: return x % 3 === 0;
      case 3: return (x + y) % 3 === 0;
      case 4: return (Math.floor(y / 2) + Math.floor(x / 3)) % 2 === 0;
      case 5: return ((x * y) % 2 + (x * y) % 3) === 0;
      case 6: return (((x * y) % 2 + (x * y) % 3) % 2) === 0;
      case 7: return (((x + y) % 2 + (x * y) % 3) % 2) === 0;
      default: return false;
    }
  }

  function drawCodewords(matrix, reserved, codewords, version, mask) {
    const bits = [];
    for (const cw of codewords) {
      for (let i = 7; i >= 0; i--) {
        bits.push(((cw >>> i) & 1) !== 0);
      }
    }
    for (let i = 0; i < REMAINDER_BITS[version]; i++) {
      bits.push(false);
    }

    const size = matrix.length;
    let bitIndex = 0;
    let upward = true;
    for (let right = size - 1; right >= 1; right -= 2) {
      if (right === 6) {
        right--;
      }
      for (let vert = 0; vert < size; vert++) {
        const y = upward ? size - 1 - vert : vert;
        for (let dx = 0; dx < 2; dx++) {
          const x = right - dx;
          if (reserved[y][x]) {
            continue;
          }
          const bit = bitIndex < bits.length ? bits[bitIndex] : false;
          matrix[y][x] = bit !== maskBit(mask, x, y);
          bitIndex++;
        }
      }
      upward = !upward;
    }
  }

  function penalty(matrix) {
    const size = matrix.length;
    let score = 0;

    for (let y = 0; y < size; y++) {
      let runColor = matrix[y][0];
      let run = 1;
      for (let x = 1; x < size; x++) {
        if (matrix[y][x] === runColor) {
          run++;
        } else {
          if (run >= 5) {
            score += 3 + run - 5;
          }
          runColor = matrix[y][x];
          run = 1;
        }
      }
      if (run >= 5) {
        score += 3 + run - 5;
      }
    }

    for (let x = 0; x < size; x++) {
      let runColor = matrix[0][x];
      let run = 1;
      for (let y = 1; y < size; y++) {
        if (matrix[y][x] === runColor) {
          run++;
        } else {
          if (run >= 5) {
            score += 3 + run - 5;
          }
          runColor = matrix[y][x];
          run = 1;
        }
      }
      if (run >= 5) {
        score += 3 + run - 5;
      }
    }

    for (let y = 0; y < size - 1; y++) {
      for (let x = 0; x < size - 1; x++) {
        const c = matrix[y][x];
        if (c === matrix[y][x + 1] && c === matrix[y + 1][x] && c === matrix[y + 1][x + 1]) {
          score += 3;
        }
      }
    }

    const finderLike = [true, false, true, true, true, false, true, false, false, false, false];
    const finderLikeRev = [false, false, false, false, true, false, true, true, true, false, true];
    for (let y = 0; y < size; y++) {
      for (let x = 0; x <= size - 11; x++) {
        const slice = matrix[y].slice(x, x + 11);
        if (matches(slice, finderLike) || matches(slice, finderLikeRev)) {
          score += 40;
        }
      }
    }
    for (let x = 0; x < size; x++) {
      for (let y = 0; y <= size - 11; y++) {
        const slice = [];
        for (let i = 0; i < 11; i++) {
          slice.push(matrix[y + i][x]);
        }
        if (matches(slice, finderLike) || matches(slice, finderLikeRev)) {
          score += 40;
        }
      }
    }

    let dark = 0;
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        if (matrix[y][x]) {
          dark++;
        }
      }
    }
    score += Math.floor(Math.abs(dark * 20 - size * size * 10) / (size * size)) * 10;
    return score;
  }

  function matches(values, pattern) {
    for (let i = 0; i < pattern.length; i++) {
      if (values[i] !== pattern[i]) {
        return false;
      }
    }
    return true;
  }

  function createQrMatrix(text) {
    const bytes = Array.from(textEncoder.encode(text));
    if (bytes.length > 216) {
      throw new Error("Name is too long after UTF-8 encoding. Use a shorter name.");
    }
    const version = chooseVersion(bytes);
    const size = version * 4 + 17;
    const base = newMatrix(size);
    const reserved = newMatrix(size);
    drawFunctionPatterns(base, reserved, version);

    const data = makeDataCodewords(bytes, version);
    const codewords = addErrorCorrection(data, version);

    let bestMatrix = null;
    let bestScore = Infinity;
    for (let mask = 0; mask < 8; mask++) {
      const candidate = cloneMatrix(base);
      drawCodewords(candidate, reserved, codewords, version, mask);
      drawFormat(candidate, mask);
      const score = penalty(candidate);
      if (score < bestScore) {
        bestScore = score;
        bestMatrix = candidate;
      }
    }
    return bestMatrix;
  }

  function sanitizeStorageName(name) {
    const cleaned = name.trim().replace(/\s+/g, " ").replace(/[^A-Za-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
    return cleaned || "qr_person";
  }

  function drawQr(canvas, matrix) {
    const quiet = 4;
    const moduleCount = matrix.length + quiet * 2;
    const scale = Math.floor(canvas.width / moduleCount);
    const size = scale * moduleCount;
    canvas.width = size;
    canvas.height = size;

    const ctx = canvas.getContext("2d");
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = "#000";
    for (let y = 0; y < matrix.length; y++) {
      for (let x = 0; x < matrix.length; x++) {
        if (matrix[y][x]) {
          ctx.fillRect((x + quiet) * scale, (y + quiet) * scale, scale, scale);
        }
      }
    }
  }

  const form = document.getElementById("qrForm");
  const nameInput = document.getElementById("name");
  const consentInput = document.getElementById("consent");
  const status = document.getElementById("status");
  const result = document.getElementById("qrResult");
  const registrationPanel = document.getElementById("registrationPanel");
  const operatorNote = document.getElementById("operatorNote");
  const canvas = document.getElementById("qrCanvas");
  const payloadLabel = document.getElementById("payloadLabel");
  const storageLabel = document.getElementById("storageLabel");
  const downloadLink = document.getElementById("downloadLink");

  function setStatus(message, type = "") {
    status.textContent = message;
    status.className = "status" + (type ? " " + type : "");
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    result.classList.remove("is-visible");

    const name = nameInput.value.trim().replace(/\s+/g, " ");
    if (!name) {
      setStatus("Enter your name.", "error");
      nameInput.focus();
      return;
    }
    if (!consentInput.checked) {
      setStatus("Consent is required before creating the QR code.", "error");
      consentInput.focus();
      return;
    }

    try {
      const matrix = createQrMatrix(name);
      const storageName = sanitizeStorageName(name);
      drawQr(canvas, matrix);
      payloadLabel.textContent = name;
      storageLabel.textContent = storageName;
      downloadLink.href = canvas.toDataURL("image/png");
      downloadLink.download = `faceassist-${storageName}-qr.png`;
      result.classList.add("is-visible");
      registrationPanel.classList.add("is-hidden");
      operatorNote.classList.add("is-hidden");
      setStatus("QR code created locally in this browser. The form was not submitted to the webserver.", "ok");
      result.scrollIntoView({behavior: "smooth", block: "start"});
    } catch (error) {
      setStatus(error && error.message ? error.message : "Could not create QR code.", "error");
    }
  });
})();
</script>
</body>
</html>
