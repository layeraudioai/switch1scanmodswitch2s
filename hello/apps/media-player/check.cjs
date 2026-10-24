const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
async function main(){
 const root=path.resolve(__dirname,'../..'),dir=await fs.mkdtemp(path.join(os.tmpdir(),'media-player-check-'));
 const state=Buffer.alloc(1024);state.writeFloatLE(1,960);
 const input=Buffer.alloc(64);input.writeUInt32LE(2,8);input.writeUInt32LE(1,32);
 await fs.writeFile(path.join(dir,'state'),state);await fs.writeFile(path.join(dir,'input'),input);
 execFileSync(path.join(root,'homebrew-launcher/game-compute-check'),[path.join(dir,'state'),path.join(dir,'output'),path.join(__dirname,'app.comp.spv'),path.join(dir,'input'),'1'],{stdio:'pipe'});
 console.log('Passed: media-player compute and render check setup.');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
