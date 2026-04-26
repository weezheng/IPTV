const input = document.getElementById("inputM3u");
const output = document.getElementById("outputM3u");
const ipPort = document.getElementById("ipPort");

function rewriteM3u(content, localIpPort) {
  const udpLineRegex = /^https?:\/\/[^\s/]+\/udp\/(\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})(\?[^\s]*)?$/gim;
  return content.replace(udpLineRegex, (_m, multicast, query = "") => {
    return `http://${localIpPort}/udp/${multicast}${query}`;
  });
}

document.getElementById("rewriteBtn").addEventListener("click", () => {
  const v = ipPort.value.trim();
  if (!v) {
    alert("请先输入本地 ip:port");
    return;
  }
  output.value = rewriteM3u(input.value, v);
});

document.getElementById("downloadBtn").addEventListener("click", () => {
  if (!output.value.trim()) {
    alert("请先生成输出内容");
    return;
  }
  const blob = new Blob([output.value], { type: "audio/x-mpegurl;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "my IPTV.m3u";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(a.href);
});
