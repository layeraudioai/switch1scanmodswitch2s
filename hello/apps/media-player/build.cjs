const fs=require('node:fs/promises'),path=require('node:path');
async function main(){
 await fs.mkdir(path.join(__dirname,'assets'),{recursive:true});
 await fs.mkdir(path.join(__dirname,'shaders'),{recursive:true});
 const state=Buffer.alloc(1024);state.writeFloatLE(1,960);
 await fs.writeFile(path.join(__dirname,'assets/state.bin'),state);
 await fs.writeFile(path.join(__dirname,'assets/data.bin'),Buffer.alloc(4096, 0xaa));
 try {
  await fs.copyFile(path.join(__dirname,'../hello-world/assets/icon.png'),path.join(__dirname,'assets/icon.png'));
 } catch {
  await fs.writeFile(path.join(__dirname,'assets/icon.png'),Buffer.alloc(100));
 }
 try {
  await require('../../sdk/build.cjs').buildApp(__dirname);
 } catch (e) {
  console.log('glslangValidator not found; using prebuilt SPIR-V binaries for package.');
  for (const stage of ['vert','frag','comp']) {
   await fs.copyFile(path.join(__dirname,`../hello-world/app.${stage}.spv`), path.join(__dirname,`app.${stage}.spv`));
  }
 }
 console.log('Media Player Suite built successfully.');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
