/* SPDX-License-Identifier: Apache-2.0 */
import com.android.server.connectivity.Y700RouteRule;
import java.nio.*;
import java.util.*;
// Synthetic address fixtures only; no deployed device identity is recorded.
public class Y700RuleRegression {
 static void require(boolean v,String m){if(!v)throw new AssertionError(m);}
 public static void main(String[] args){
  int tests=0;
  for(String value:new String[]{"192.0.2.1","10.0.0.1","172.16.1.254","169.254.23.1","223.255.255.254"}){require(Y700RouteRule.isDeviceAddress(value),value);tests++;}
  for(String value:new String[]{"","1.2.3","256.1.2.3","127.0.0.1","0.1.2.3","224.0.0.1","255.255.255.255","192.168.01.1","1.2.3.4/24","example.com","1.2.3.4;reboot","-1.1.1.1","1.2.3.4\n1.2.3.5"}){require(!Y700RouteRule.isDeviceAddress(value),value);tests++;}
  for(int mark:new int[]{0,100,65535})for(int protocol:new int[]{0,6,17}){
   Y700RouteRule rule=new Y700RouteRule("192.0.2.1",1007,mark,protocol);
   byte[] add=rule.message(true),del=rule.message(false);ByteBuffer b=ByteBuffer.wrap(add).order(ByteOrder.nativeOrder());
   require(b.getInt(0)==add.length && b.getShort(4)==32 && b.getShort(6)==0x605,"header");
   require(b.get(16)==2 && b.get(17)==32 && b.get(23)==1,"fib header");
   require(ByteBuffer.wrap(del).order(ByteOrder.nativeOrder()).getShort(4)==33,"delete");
   List<byte[]> owned=Y700RouteRule.ownedDeletes(b);require(owned.size()==1,"owned detection");
   require(Arrays.equals(owned.get(0),del),"dump deletion preserves exact attributes");
   byte[] other=add.clone();for(int at=28;at<other.length;){ByteBuffer v=ByteBuffer.wrap(other).order(ByteOrder.nativeOrder());int n=v.getShort(at)&65535,t=v.getShort(at+2)&65535;if(t==21)other[at+4]=4;at+=(n+3)&~3;}
   require(Y700RouteRule.ownedDeletes(ByteBuffer.wrap(other)).isEmpty(),"foreign protocol retained");tests++;
  }
  for(int mark:new int[]{-1,65536,0x10064})try{new Y700RouteRule("192.0.2.1",1002,mark,0);throw new AssertionError("bad mark accepted");}catch(IllegalArgumentException ok){tests++;}
  require(Y700RouteRule.ownedDeletes(ByteBuffer.wrap(new byte[5])).isEmpty(),"short input");
  System.out.println("PASS: "+tests+" rule codec and address cases; exact owned-only cleanup, explicit bindings excluded");
 }
}
