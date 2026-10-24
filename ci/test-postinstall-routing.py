#!/usr/bin/env python3
"""Run the actual MountPartition body with fake block/mount/SELinux services."""
from pathlib import Path
import argparse,subprocess,tempfile,shutil,json
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);a=p.parse_args()
text=(a.source/'system/update_engine/payload_consumer/postinstall_runner_action.cc').read_text()
start=text.index('bool PostinstallRunnerAction::MountPartition(');opening=text.index('{',start);depth=1;end=opening+1
while depth:
 if text[end]=='{':depth+=1
 elif text[end]=='}':depth-=1
 end+=1
body=text[start:end]
prefix=r'''
#include <sys/mount.h>
#include <sys/wait.h>
#include <cstdint>
#include <cstdlib>
#include <vector>
#include <string>
#include <iostream>
#include <cassert>
using std::string;
namespace brillo { using Blob=std::vector<uint8_t>; }
struct State { int hooks=0,reads=0,mounts=0,contexts=0,count=2,ret=0; bool readfail=false,shortread=false,mountfail=false,contextfail=false,gapps=false,magisk=false; } st;
namespace utils {
bool FileExists(const char* p) { string s(p); if(s=="/system/addon.d/30-gapps.sh")return st.gapps; if(s=="/system/addon.d/99-magisk.sh")return st.magisk;return true; }
bool ReadFileChunk(const string&,int,size_t,brillo::Blob* b) {++st.reads;if(st.readfail)return false;if(st.shortread){b->assign(1,0);return true;}b->assign({static_cast<uint8_t>(st.count),0});return true;}
bool SetBlockDeviceReadOnly(const string&,bool) {return true;}
bool MountFilesystem(const string&,const string&,unsigned long,const string&,const string&) {++st.mounts;return !st.mountfail;}
bool UnmountFilesystem(const string&) {return true;}
}
int setexeccon(const char*) {++st.contexts;return st.contextfail ? -1:0;}
int FakeSystem(const char* cmd) {assert(string(cmd)=="/postinstall/system/bin/backuptool_postinstall.sh");++st.hooks;return st.ret;}
struct BootControlInterface {static constexpr int kInvalidSlot=-1;};
struct FakeBoot { bool GetPartitionDevice(const string&,int,string* out){*out="/fake/source";return true;} } boot;
struct FakeHardware { string GetPartitionMountOptions(const string&){return "";} } hardware;
struct InstallPlan {struct Partition {string name,readonly_target_path="/fake/target",filesystem_type="ext4";}; int source_slot=0;};
struct PostinstallRunnerAction {InstallPlan install_plan_;FakeBoot* boot_control_=&boot;FakeHardware* hardware_=&hardware;string fs_mount_dir_="/postinstall";void EnsureUnmounted(){};bool MountPartition(const InstallPlan::Partition&) noexcept;};
#define __ANDROID__ 1
#define RUN_BACKUPTOOL 1
#define LOG(x) std::cerr
#define PLOG(x) std::cerr
#define system FakeSystem
'''
tests=r'''
int main(){
 PostinstallRunnerAction action;InstallPlan::Partition part;
 st={};part.name="vendor";assert(action.MountPartition(part));assert(st.hooks==0 && st.reads==0 && st.mounts==1);
 st={};part.name="system";assert(action.MountPartition(part));assert(st.hooks==1 && st.reads==1 && st.contexts==2 && st.mounts==2);
 st={};st.ret=127<<8;assert(!action.MountPartition(part));assert(st.hooks==1 && st.contexts==2);
 st={};st.ret=9;assert(!action.MountPartition(part));assert(st.contexts==2);
 st={};st.readfail=true;assert(!action.MountPartition(part));assert(st.hooks==0);
 st={};st.shortread=true;assert(!action.MountPartition(part));assert(st.hooks==0);
 st={};st.count=0;st.gapps=true;assert(action.MountPartition(part));assert(st.hooks==1);
 st={};st.count=0;st.magisk=true;assert(action.MountPartition(part));assert(st.hooks==1);
 st={};st.count=0;assert(action.MountPartition(part));assert(st.hooks==0);
 st={};st.mountfail=true;assert(!action.MountPartition(part));assert(st.hooks==0);
 st={};st.contextfail=true;assert(!action.MountPartition(part));assert(st.hooks==0);
 std::cout<<"PASS: 11 actual postinstall routing/failure cases; no real mounts, devices, SELinux changes or shell hooks"<<std::endl;
}
'''
compiler=shutil.which('g++') or shutil.which('clang++');assert compiler,'Host C++ compiler required for routing regression'
with tempfile.TemporaryDirectory(prefix='y700-postinstall-routing-') as td:
 d=Path(td);cpp=d/'routing.cc';exe=d/'routing';cpp.write_text(prefix+'\n'+body+'\n'+tests)
 subprocess.run([compiler,'-std=c++17','-Wall','-Werror',str(cpp),'-o',str(exe)],check=True)
 r=subprocess.run([str(exe)],capture_output=True,text=True,check=True);print(r.stdout.strip())
