export async function showStl(url, preview) {
  const pctx = preview.getContext("2d");
  const buffer = await fetch(url).then((res) => res.arrayBuffer());
  const view = new DataView(buffer);
  const count = view.getUint32(80, true);
  const triangles = [];
  let offset = 84;
  for (let i = 0; i < count && offset + 50 <= buffer.byteLength; i++) {
    offset += 12;
    const tri = [];
    for (let v = 0; v < 3; v++) {
      tri.push([view.getFloat32(offset, true), view.getFloat32(offset + 4, true), view.getFloat32(offset + 8, true)]);
      offset += 12;
    }
    triangles.push(tri);
    offset += 2;
  }
  pctx.clearRect(0, 0, preview.width, preview.height);
  // Isometric projection keeps the plate face and pocket visible in every axis convention.
  const project = p => [(p[0] - p[1]) / Math.sqrt(2),
    (p[0] + p[1] - 2 * p[2]) / Math.sqrt(6)];
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const tri of triangles) for (const p of tri) {
    const [x, y] = project(p);
    minX = Math.min(minX, x); maxX = Math.max(maxX, x);
    minY = Math.min(minY, y); maxY = Math.max(maxY, y);
  }
  const scale = Math.min(preview.width / (maxX - minX || 1), preview.height / (maxY - minY || 1)) * 0.85;
  const ox = preview.width / 2, oy = preview.height / 2;
  const pixels = pctx.createImageData(preview.width, preview.height);
  const depths = new Float64Array(preview.width * preview.height).fill(-Infinity);
  for (const tri of triangles) {
    const u = tri[1].map((v, i) => v - tri[0][i]);
    const v = tri[2].map((v, i) => v - tri[0][i]);
    const n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]];
    const length = Math.hypot(...n) || 1;
    const light = Math.max(0, (0.3*n[0]+0.5*n[1]+0.8*n[2])/length);
    const shade = Math.round(75 + 115 * light);
    const projected = tri.map(p => {
      const q = project(p);
      return [ox + (q[0] - (minX + maxX) / 2) * scale,
        oy + (q[1] - (minY + maxY) / 2) * scale, p[0] + p[1] + p[2]];
    });
    const [a, b, c] = projected;
    const denominator = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1]);
    if (Math.abs(denominator) < 1e-8) continue;
    const x0 = Math.max(0, Math.floor(Math.min(a[0], b[0], c[0])));
    const x1 = Math.min(preview.width-1, Math.ceil(Math.max(a[0], b[0], c[0])));
    const y0 = Math.max(0, Math.floor(Math.min(a[1], b[1], c[1])));
    const y1 = Math.min(preview.height-1, Math.ceil(Math.max(a[1], b[1], c[1])));
    // Depth per pixel is necessary: sorting whole triangles fails around holes and pockets.
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      const wa = ((b[1]-c[1])*(x+0.5-c[0]) + (c[0]-b[0])*(y+0.5-c[1])) / denominator;
      const wb = ((c[1]-a[1])*(x+0.5-c[0]) + (a[0]-c[0])*(y+0.5-c[1])) / denominator;
      const wc = 1-wa-wb;
      if (Math.min(wa,wb,wc) < -1e-8) continue;
      const z = wa*a[2] + wb*b[2] + wc*c[2];
      const offset = y*preview.width+x;
      if (z <= depths[offset]) continue;
      depths[offset] = z;
      pixels.data.set([shade, shade+7, shade+10, 255], offset*4);
    }
  }
  pctx.putImageData(pixels, 0, 0);
  preview.hidden = false;
}
