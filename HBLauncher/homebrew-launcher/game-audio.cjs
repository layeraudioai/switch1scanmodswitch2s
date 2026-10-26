// Synthesized game effects. No ROM, downloaded samples, or injected CPU code.
const fs=require('node:fs/promises'),path=require('node:path');
const symbols=require('./audio-symbols.json');
const check=(v,m)=>{if(!v)throw Error(m);};
function synth(kind){
 const rate=48000,duration=[0,.035,.065,.11,.32,.45,.08,.18][kind],frames=Math.ceil(rate*duration),pcm=Buffer.alloc(frames*4);
 for(let i=0;i<frames;i++){
  const t=i/rate,u=t/duration,attack=Math.min(1,t/.004),envelope=attack*Math.pow(1-u,1.7);
  let frequency=kind===1?240:kind===2?440+u*230:kind===3?140-u*65:kind===5?440*Math.pow(.23,u):kind===6?660:523.25;
  if(kind===4)frequency=[523.25,659.25,783.99,1046.5][Math.min(3,Math.floor(u*4))];
  if(kind===7)frequency=[392,523.25,659.25][Math.min(2,Math.floor(u*3))];
  const fundamental=Math.sin(2*Math.PI*frequency*t),overtone=Math.sin(4*Math.PI*frequency*t)*.18;
  const sample=Math.round(32767*.19*envelope*(fundamental+overtone));pcm.writeInt16LE(sample,i*4);pcm.writeInt16LE(sample,i*4+2);
 }
 return pcm;
}
async function main(directory){
 directory=path.resolve(directory);const rpc=require(path.join(directory,'shared/rpc.cjs'));
 
 let stop=false,started=false,audio;process.on('SIGINT',()=>stop=true);process.on('SIGTERM',()=>stop=true);
 
 console.log('[AUDIO] Waiting for game-audio-source.json...');
 let source;
 while(!stop){
  try {
   source = JSON.parse(await fs.readFile(path.join(directory,'game-audio-source.json')));
   if (source && source.session === rpc.a.session) break;
  } catch(e) {}
  await new Promise(r => setTimeout(r, 100));
 }
 if(stop) return;
 console.log('[AUDIO] Audio source session detected.');

 const file=path.join(directory,'game-audio.json'),report={session:rpc.a.session,started:new Date().toISOString(),functions:{},resourcesRetained:true,played:0,history:[]};
 await fs.writeFile(file,'{}',{flag:'wx'});
 const save=()=>fs.writeFile(file,JSON.stringify(report,null,2));const sdkImage=require('../smilebasic/reference/sdk-checks.cjs');
 async function call(name,...args){
  if(!report.functions[name]){const matches=symbols.filter(s=>s.name.includes(name));check(matches.length===1,'Ambiguous sound symbol '+name);const s=matches[0],address=rpc.a.sdk+s.offset;await rpc.request({command:'verify-function',address,hex:sdkImage.bytes(s.offset,Math.min(32,s.size)).toString('hex')});report.functions[name]=address;}
  return (await rpc.callAddress(report.functions[name],args)).result;
 }
 try{
  const bytes=65536+31*131072,temp=rpc.a.scratch+0x10000,saved=await rpc.read(temp,8);let base;
  try{check((await rpc.call(5732112,[temp,65536,bytes])).result===0n,'Sound allocation failed');base=Number((await rpc.read(temp,8)).readBigUInt64LE());}finally{await rpc.write(temp,saved);}
  check(Number.isSafeInteger(base)&&base>0&&base%65536===0,'Invalid sound allocation');audio=base;report.audio=audio;report.base=base;
  await rpc.write(base,Buffer.alloc(65536));let sounds={};
  const param=base+0x300;await call('InitializeAudioOutParameter',param);const params=await rpc.read(param,8);params.writeUInt32LE(48000);params.writeUInt16LE(2,4);await rpc.write(param,params);
  check((await call('OpenDefaultAudioOutEPNS0_8AudioOutER',audio,param))===0n,'Game audio output failed');
  check((await call('GetAudioOutSampleRate',audio))===48000n&&(await call('GetAudioOutChannelCount',audio))===2n&&(await call('GetAudioOutSampleFormat',audio))===2n,'Unexpected game audio format');
  const descriptors=new Set(Array.from({length:8},(_,i)=>base+0x400+i*0x40)),free=new Set(descriptors);
  async function release(){for(let i=0;i<8;i++){const address=await call('GetReleasedAudioOutBuffer',audio);if(address===0n)break;check(descriptors.has(Number(address)),'Unknown sound descriptor');free.add(Number(address));}}
  
  let currentFFmpeg = null;

  async function play(kind){
   if (currentFFmpeg) {
    try { currentFFmpeg.kill(); } catch(e) {}
    currentFFmpeg = null;
   }

   const packageInfo = report.package;
   if(!packageInfo) return;
   const appContentDir = path.resolve(directory, '../../apps', packageInfo.id, 'content');
   let files = [];
   try {
    const entries = await fs.readdir(appContentDir);
    files = entries.filter(name => !name.startsWith('.')).sort();
   } catch(e) {}
   
   const fileIndex = kind - 1;
   if (fileIndex < 0 || fileIndex >= files.length) return;
   const mediaFile = path.join(appContentDir, files[fileIndex]);
   
   console.log(`[AUDIO] Streaming media file on-the-fly: ${mediaFile}`);
   
   const {spawn} = require('node:child_process');
   const ffmpegProcess = spawn('ffmpeg', [
    '-i', mediaFile,
    '-f', 's16le',
    '-acodec', 'pcm_s16le',
    '-ar', '48000',
    '-ac', '2',
    'pipe:1'
   ], {stdio: ['ignore', 'pipe', 'pipe']});
   
   currentFFmpeg = ffmpegProcess;
   
   ffmpegProcess.stderr.on('data', (data) => {
    console.error(`[FFMPEG] ${data.toString().trim()}`);
   });
   
   try {
    let chunkQueue = [];
    let isFinished = false;
    
    ffmpegProcess.stdout.on('data', (data) => {
     chunkQueue.push(data);
    });
    ffmpegProcess.on('close', (code) => {
     console.log(`[FFMPEG] Process exited with code ${code}`);
     isFinished = true;
    });
    
    async function readNextChunk() {
     while (chunkQueue.length === 0 && !isFinished && !stop && currentFFmpeg === ffmpegProcess) {
      await new Promise(r => setTimeout(r, 20));
     }
     if (currentFFmpeg !== ffmpegProcess) return null;
     if (chunkQueue.length === 0) return null;
     
     let totalLen = chunkQueue.reduce((acc, c) => acc + c.length, 0);
     let combined = Buffer.concat(chunkQueue, totalLen);
     chunkQueue = [];
     
     if (combined.length > 131072) {
      chunkQueue.push(combined.subarray(131072));
      combined = combined.subarray(0, 131072);
     }
     
     if (combined.length < 131072) {
      const padded = Buffer.alloc(131072);
      combined.copy(padded);
      combined = padded;
     }
     
     const rem = combined.length % 4;
     if (rem !== 0) combined = combined.subarray(0, combined.length - rem);
     
     return combined;
    }
    
    const soundAddress = base + 65536 + (Math.max(1, kind) - 1) * 131072;
    
    while (!stop && currentFFmpeg === ffmpegProcess) {
     const chunk = await readNextChunk();
     if (!chunk) break;
     
     while(free.size === 0 && !stop && currentFFmpeg === ffmpegProcess) {
      await release();
      if(free.size === 0) await new Promise(r => setTimeout(r, 10));
     }
     if(stop || currentFFmpeg !== ffmpegProcess) break;
     
     const descriptor = free.values().next().value;
     await rpc.write(soundAddress, chunk);
     await call('SetAudioOutBufferInfo', descriptor, soundAddress, 131072, chunk.length);
     check((await call('AppendAudioOutBuffer', audio, descriptor)) === 1n, 'Sound buffer rejected');
     free.delete(descriptor);
     
     if(!started) {
      check((await call('StartAudioOut', audio)) === 0n, 'Sound playback failed');
      started = true;
     }
     
     report.played++;
     report.history.push({kind, file: files[fileIndex], time: new Date().toISOString()});
     report.history = report.history.slice(-64);
     await save();
    }
   } finally {
    if (currentFFmpeg === ffmpegProcess) currentFFmpeg = null;
    try { ffmpegProcess.kill(); } catch(e) {}
   }
  }

  report.ready=true;await save();console.log('Game sound effects ready.');
  let sequence=-1,token=null;
  async function loadEffects(packageInfo){
   if(started){check((await call('StopAudioOut',audio))===0n,'Sound pause failed');started=false;}
   await call('FlushAudioOutBuffers',audio);await release();check(Number(await call('GetAudioOutBufferCount',audio))===0,'Sound queue did not drain');free.clear();for(const descriptor of descriptors)free.add(descriptor);sounds={};
   for(const [key,file]of Object.entries(packageInfo?.effects||{})){
    const kind=Number(key);check(Number.isInteger(kind)&&kind>=1&&kind<=31,'Invalid sound event id');
    const stat=await fs.stat(file);check(stat.size>0&&stat.size%4===0,'Invalid package PCM size');
    const address=base+65536+(kind-1)*131072;
    sounds[kind]={address,file,size:stat.size};
   }
   token=packageInfo?.fingerprint||null;sequence=-1;report.package=packageInfo?{id:packageInfo.id,fingerprint:token,effects:Object.keys(sounds)}:null;await save();
  }
  while(!stop){
   const current=JSON.parse(await fs.readFile(path.join(directory,'game-audio-source.json')));check(current.session===rpc.a.session,'Sound source session changed');
   if((current.package?.fingerprint||null)!==token)await loadEffects(current.package||null);
   await release();const state=await rpc.read(source.mapped+784,208),next=state.readUInt32LE(192),kind=state.readUInt32LE(196);
   if (next !== sequence) {
    console.log(`[AUDIO POLL] Event detected! next: ${next}, sequence: ${sequence}, kind: ${kind}`);
   }
   if(next!==sequence){sequence=next;if(next!==0)await play(kind);}
   await new Promise(resolve=>setTimeout(resolve,50));
  }
 }catch(error){report.error=error.stack;console.error(error);process.exitCode=1;}
 finally{if(started)try{await call('StopAudioOut',audio);}catch(error){report.stopError=error.message;}report.completed=new Date().toISOString();await save();}
}
module.exports={synth};
if(require.main===module)main(process.argv[2]).catch(error=>{console.error(error);process.exitCode=1;});
