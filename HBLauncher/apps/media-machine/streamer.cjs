const { spawn } = require('node:child_process');
const fs = require('node:fs/promises');
const path = require('node:path');

class MediaMachineStreamer {
    constructor(appRoot) {
        this.appRoot = appRoot;
        this.cacheDir = path.join(appRoot, 'assets', 'segments');
        this.segmentDuration = 60; // seconds
        this.fps = 50;
        this.width = 1600;
        this.height = 900;
        this.frameBytes = this.width * this.height * 2;
    }

    async init() {
        await fs.mkdir(this.cacheDir, { recursive: true });
    }

    async getFrame(clipIndex, sourcePath, targetFrame) {
        const frameTime = targetFrame / this.fps;
        const currentSegmentIndex = Math.floor(frameTime / this.segmentDuration);
        const nextSegmentIndex = currentSegmentIndex + 1;

        // Ensure current and next 60s segments are available (sliding window)
        await this.ensureSegment(clipIndex, sourcePath, currentSegmentIndex);
        await this.ensureSegment(clipIndex, sourcePath, nextSegmentIndex);

        // Clean up segments outside window, protecting segments 0 and 1 (first 120s)
        await this.cleanupSegments(clipIndex, [currentSegmentIndex, nextSegmentIndex]);

        const segmentIndex = Math.floor(frameTime / this.segmentDuration);
        const localTime = frameTime - (segmentIndex * this.segmentDuration);
        const localFrame = Math.floor(localTime * this.fps);
        const maxFramesInSegment = this.segmentDuration * this.fps;
        const clampedFrame = Math.max(0, Math.min(localFrame, maxFramesInSegment - 1));

        const segmentPath = this.getSegmentPath(clipIndex, segmentIndex);
        try {
            const fh = await fs.open(segmentPath, 'r');
            try {
                const buf = Buffer.alloc(this.frameBytes);
                const { bytesRead } = await fh.read(buf, 0, this.frameBytes, clampedFrame * this.frameBytes);
                if (bytesRead > 0) return buf;
            } finally {
                await fh.close();
            }
        } catch (e) {
            // Segment loading fallback
        }
        return Buffer.alloc(this.frameBytes);
    }

    getSegmentPath(clipIndex, segmentIndex) {
        return path.join(this.cacheDir, `clip_${clipIndex}_seg_${segmentIndex}.rgb565`);
    }

    async ensureSegment(clipIndex, sourcePath, segmentIndex) {
        const segmentPath = this.getSegmentPath(clipIndex, segmentIndex);
        try {
            const stat = await fs.stat(segmentPath);
            if (stat.size > 0) return;
        } catch (e) {}

        const startTime = segmentIndex * this.segmentDuration;
        const tempOut = `${segmentPath}.tmp`;
        const cmd = [
            'ffmpeg', '-v', 'error',
            '-ss', String(startTime),
            '-i', sourcePath,
            '-t', String(this.segmentDuration),
            '-an', '-sn', '-dn', '-q', '0', '-lossless', 'true',
            '-filter_complex:v', `fps=${this.fps},scale=${this.width}:${this.height}:force_original_aspect_ratio=increase,crop=${this.width}:${this.height}`,
            '-f', 'rawvideo', '-pix_fmt', 'rgb565le', '-y', tempOut
        ];

        try {
            await new Promise((resolve, reject) => {
                const p = spawn(cmd[0], cmd.slice(1), { stdio: 'ignore' });
                p.on('close', (code) => {
                    if (code === 0) resolve();
                    else reject(new Error(`FFmpeg exited with code ${code}`));
                });
                p.on('error', reject);
            });
            await fs.rename(tempOut, segmentPath);
        } catch (err) {
            try { await fs.unlink(tempOut); } catch (ex) {}
            console.error(`[MediaMachineStreamer] Failed to encode segment ${segmentIndex} for clip ${clipIndex}:`, err.message);
        }
    }

    async cleanupSegments(clipIndex, keepIndices) {
        try {
            const files = await fs.readdir(this.cacheDir);
            for (const file of files) {
                if (file.startsWith(`clip_${clipIndex}_seg_`) && file.endsWith('.rgb565')) {
                    const match = file.match(/seg_(\d+)\.rgb565/);
                    if (match) {
                        const segIdx = parseInt(match[1], 10);
                        // Ensure the first 120 seconds (segments 0 and 1) are never replaced or deleted
                        if (segIdx === 0 || segIdx === 1) continue;
                        if (!keepIndices.includes(segIdx)) {
                            await fs.unlink(path.join(this.cacheDir, file)).catch(() => {});
                        }
                    }
                }
            }
        } catch (e) {}
    }
}

module.exports = { MediaMachineStreamer };
