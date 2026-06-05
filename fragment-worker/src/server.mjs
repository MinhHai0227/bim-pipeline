import http from "node:http";
import path from "node:path";
import { mkdir, readFile, stat, writeFile } from "node:fs/promises";

import * as FRAGS from "@thatopen/fragments";

const PORT = Number.parseInt(process.env.PORT || "8090", 10);
const WORK_DIR = path.resolve(process.env.FRAGMENT_WORK_DIR || "/tmp/bim-pipeline/ifc");
const DEFAULT_WASM_PATH = "/app/node_modules/web-ifc";
const WEB_IFC_WASM_PATH = process.env.WEB_IFC_WASM_PATH || DEFAULT_WASM_PATH;

function jsonResponse(res, statusCode, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(statusCode, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => {
      chunks.push(chunk);
    });
    req.on("end", () => {
      try {
        const rawBody = Buffer.concat(chunks).toString("utf8");
        resolve(rawBody ? JSON.parse(rawBody) : {});
      } catch (error) {
        reject(new Error(`Invalid JSON body: ${error.message}`));
      }
    });
    req.on("error", reject);
  });
}

function resolveInsideWorkDir(filePath) {
  if (!filePath || typeof filePath !== "string") {
    throw new Error("inputPath and outputPath are required.");
  }

  const resolvedPath = path.resolve(filePath);
  const allowedPrefix = `${WORK_DIR}${path.sep}`;

  if (resolvedPath !== WORK_DIR && !resolvedPath.startsWith(allowedPrefix)) {
    throw new Error(`Path must stay inside ${WORK_DIR}.`);
  }

  return resolvedPath;
}

function toBuffer(bytes) {
  if (Buffer.isBuffer(bytes)) {
    return bytes;
  }

  if (bytes instanceof Uint8Array) {
    return Buffer.from(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  }

  if (bytes instanceof ArrayBuffer) {
    return Buffer.from(bytes);
  }

  throw new Error("Unsupported fragment output type.");
}

async function convertIfcToFragments(inputPath, outputPath) {
  const start = Date.now();
  const ifcBuffer = await readFile(inputPath);
  const serializer = new FRAGS.IfcImporter();

  serializer.wasm = {
    absolute: true,
    path: WEB_IFC_WASM_PATH.endsWith(path.sep)
      ? WEB_IFC_WASM_PATH
      : `${WEB_IFC_WASM_PATH}${path.sep}`,
  };

  const fragmentBytes = await serializer.process({
    bytes: new Uint8Array(ifcBuffer),
  });
  const outputBuffer = toBuffer(fragmentBytes);

  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, outputBuffer);

  return {
    inputPath,
    outputPath,
    sizeBytes: outputBuffer.byteLength,
    durationMs: Date.now() - start,
  };
}

async function handleConvert(req, res) {
  try {
    const body = await readJsonBody(req);
    const inputPath = resolveInsideWorkDir(body.inputPath);
    const outputPath = resolveInsideWorkDir(body.outputPath);

    await stat(inputPath);
    const result = await convertIfcToFragments(inputPath, outputPath);
    jsonResponse(res, 200, { status: "ok", ...result });
  } catch (error) {
    jsonResponse(res, 500, {
      status: "error",
      message: error.message,
    });
  }
}

const server = http.createServer(async (req, res) => {
  if (req.method === "GET" && req.url === "/health") {
    jsonResponse(res, 200, {
      status: "ok",
      service: "fragment-worker",
      workDir: WORK_DIR,
      wasmPath: WEB_IFC_WASM_PATH,
    });
    return;
  }

  if (req.method === "POST" && req.url === "/convert") {
    await handleConvert(req, res);
    return;
  }

  jsonResponse(res, 404, {
    status: "error",
    message: "Route not found.",
  });
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`fragment-worker listening on :${PORT}`);
  console.log(`fragment-worker work dir: ${WORK_DIR}`);
  console.log(`web-ifc wasm path: ${WEB_IFC_WASM_PATH}`);
});
