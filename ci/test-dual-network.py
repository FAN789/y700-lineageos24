"""Compile and exercise the actual pure Java rule encoder and NetworkRanker control flow."""
from pathlib import Path
import argparse,tempfile,subprocess,shutil
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);a=p.parse_args();s=a.source;ci=Path(__file__).resolve().parent;j=s/'prebuilts/jdk/jdk21/linux-x86/bin';n=s/'packages/modules/Connectivity/service/src/com/android/server/connectivity'
with tempfile.TemporaryDirectory(prefix='y700-dualnet-test-') as td:
 t=Path(td);classes=t/'classes';classes.mkdir();src=t/'src';src.mkdir()
 def put(name,text):
  p=src/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
 for annotation in ['NonNull','Nullable']:
  put('android/annotation/'+annotation+'.java','package android.annotation; public @interface '+annotation+' {}')
 put('com/android/internal/annotations/VisibleForTesting.java','package com.android.internal.annotations; public @interface VisibleForTesting {}')
 put('android/net/NetworkScore.java','package android.net; public class NetworkScore { public static final int POLICY_EXITING=1,POLICY_TRANSPORT_PRIMARY=2,POLICY_VCN=3,POLICY_YIELD_TO_BAD_WIFI=4; }')
 put('android/net/NetworkCapabilities.java','''package android.net; public class NetworkCapabilities {public static final int NET_CAPABILITY_CAPTIVE_PORTAL=17,TRANSPORT_BLUETOOTH=2,TRANSPORT_CELLULAR=0,TRANSPORT_ETHERNET=3,TRANSPORT_WIFI=1;private int transport; public NetworkCapabilities(int t){transport=t;}public boolean hasTransport(int t){return t==transport;}public boolean hasCapability(int c){return false;}public int[] getTransportTypes(){return new int[]{transport};}}''')
 put('android/net/NetworkRequest.java','''package android.net; public class NetworkRequest {private int transport;public NetworkRequest(int t){transport=t;}public boolean canBeSatisfiedBy(NetworkCapabilities c){return transport<0||c.hasTransport(transport);}}''')
 constants=['POLICY_ACCEPT_UNVALIDATED','POLICY_AVOIDED_WHEN_UNVALIDATED','POLICY_EVER_EVALUATED','POLICY_EVER_USER_SELECTED','POLICY_EVER_VALIDATED','POLICY_IS_DESTROYED','POLICY_IS_INVINCIBLE','POLICY_IS_VALIDATED','POLICY_IS_VPN']
 put('com/android/server/connectivity/FullScore.java','package com.android.server.connectivity;import java.util.*;public class FullScore {'+' public static final int '+','.join(k+'='+str(10+i) for i,k in enumerate(constants))+';private Set<Integer> policies=new HashSet<>();public FullScore(int...p){for(int v:p)policies.add(v);}public boolean hasPolicy(int p){return policies.contains(p);}}')
 put('com/android/server/connectivity/NetworkAgentInfo.java','''package com.android.server.connectivity;import android.net.*;public class NetworkAgentInfo implements NetworkRanker.Scoreable {private NetworkCapabilities c;private FullScore s;public NetworkAgentInfo(int t,int...flags){c=new NetworkCapabilities(t);s=new FullScore(flags);}public FullScore getScore(){return s;}public NetworkCapabilities getCapsNoCopy(){return c;}public boolean satisfies(NetworkRequest r){return r.canBeSatisfiedBy(c);}}''')
 put('com/android/net/module/util/CollectionUtils.java','''package com.android.net.module.util;import java.util.*;import java.util.function.*;public class CollectionUtils {public static <T> ArrayList<T> filter(Collection<T> a,Predicate<T> p){ArrayList<T> r=new ArrayList<>();for(T v:a)if(p.test(v))r.add(v);return r;}public static <T> boolean any(Collection<T>a,Predicate<T>p){for(T v:a)if(p.test(v))return true;return false;}public static <T> boolean all(Collection<T>a,Predicate<T>p){for(T v:a)if(!p.test(v))return false;return true;}}''')
 put('Y700RankRegression.java','''import java.util.*;import android.net.*;import com.android.server.connectivity.*;import static com.android.server.connectivity.FullScore.*;
public class Y700RankRegression {static int cases;static void check(NetworkRanker r,NetworkAgentInfo expected,NetworkAgentInfo...nodes){NetworkAgentInfo got=r.getBestNetwork(new NetworkRequest(-1),Arrays.asList(nodes),null);if(got!=expected)throw new AssertionError("rank case "+cases);cases++;}public static void main(String[]args){
for(boolean avoid:new boolean[]{false,true})for(int preference:new int[]{-1,1,3}){
NetworkRanker r=new NetworkRanker(new NetworkRanker.Configuration(avoid,preference));NetworkAgentInfo wifi=new NetworkAgentInfo(1,POLICY_IS_VALIDATED),eth=new NetworkAgentInfo(3,POLICY_IS_VALIDATED),badWifi=new NetworkAgentInfo(1),badEth=new NetworkAgentInfo(3),vpn=new NetworkAgentInfo(4,POLICY_IS_VPN),cell=new NetworkAgentInfo(0,POLICY_IS_VALIDATED);
check(r,preference==1?wifi:eth,wifi,eth);check(r,preference==1?badWifi:eth,badWifi,eth);check(r,preference==3?badEth:wifi,wifi,badEth);check(r,vpn,wifi,eth,vpn);check(r,vpn,vpn,badEth,badWifi);check(r,preference==1?badWifi:cell,badWifi,cell);check(r,preference==3?badEth:cell,badEth,cell);check(r,wifi,wifi);check(r,eth,eth);if(r.getBestNetwork(new NetworkRequest(3),Arrays.asList(wifi,eth),null)!=eth)throw new AssertionError("explicit request");cases++;if(r.getBestNetwork(new NetworkRequest(1),Arrays.asList(wifi,eth),null)!=wifi)throw new AssertionError("wifi request");cases++;
}
System.out.println("PASS: "+cases+" actual NetworkRanker preference, automatic validation fallback, explicit manual outlet, VPN and transport-constrained request cases; Android types are minimal host stubs");}}''')
 for name in ['NetworkRanker.java','Y700RouteRule.java']:shutil.copyfile(n/name,put('com/android/server/connectivity/'+name,''))
 shutil.copyfile(ci/'Y700RuleRegression.java',put('Y700RuleRegression.java',''))
 args=[str(j/'javac'),'--release','17','-d',str(classes),*map(str,src.rglob('*.java'))]
 r=subprocess.run(args,capture_output=True,text=True);assert r.returncode==0,r.stderr
 for main in ['Y700RankRegression','Y700RuleRegression']:
  r=subprocess.run([str(j/'java'),'-cp',str(classes),main],capture_output=True,text=True);assert r.returncode==0,r.stderr;print(r.stdout.strip())
