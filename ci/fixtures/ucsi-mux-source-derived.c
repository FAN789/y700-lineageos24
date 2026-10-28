/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact reviewed original/candidate UCSI C blocks; isolated GPIO stubs only. */
#include <assert.h>
#include <stdio.h>
#define UCSI_CONSTAT_PWR_OPMODE_TYPEC3_0 5
#define printk(...) ((void)0)
#define mdelay(x) ((void)0)
static int C1_d_present,C2_d_present,gpio_state;
static int gpio_get_value(int pin){assert(pin==389);return gpio_state;}
static void gpio_set_value(int pin,int value){assert(pin==389);gpio_state=value;}
static int run_original(int con,int change,int partner_usb,int conn_partner_type,int conn_power_mode,int flags,int initial,int gpio){
 int a=0;C1_d_present=initial&1;C2_d_present=(initial>>1)&1;gpio_state=gpio;
	if(con!=0 && change!=0 && partner_usb == 1&&(conn_partner_type==1||conn_partner_type==2)&&(conn_power_mode==4||conn_power_mode==1))
	{
		if(con==1){
			C1_d_present = 1;
			printk("+++++C1 data PORT++++++++");
				}
		else if (con==2){
			C2_d_present = 1;
			printk("+++++C2 data PORT++++++++");
				}
		else
			printk("++++++No data port+++++++");
	  }else if((con!=0 && change!=0 && partner_usb == 1 && conn_partner_type==1 && conn_power_mode==3) ||
		(con!=0 && change!=0 && partner_usb == 1 && conn_partner_type==0 && conn_power_mode==4)){
		  //c to c connected PC
                if(con==1){
                        C1_d_present = 1;
                        printk("+++++C1 data PORT++++++++");
                                }
                else if (con==2){
                        C2_d_present = 1;
                        printk("+++++C2 data PORT++++++++");
                                }
                else
                        printk("++++++No data port+++++++");
          }else if(con!=0 && change!=0 && partner_usb == 1 && conn_partner_type==4 && (conn_power_mode==3||conn_power_mode==4)){
		if(con==1){
			C1_d_present = 1;
			printk("+++++C1 data PORT++++++++");
				}
		else if (con==2){
			C2_d_present = 1;
			printk("+++++C2 data PORT++++++++");
				}
		else
			printk("++++++No data port+++++++");
          }else if(con!=0 && change!=0 && partner_usb == 1 && conn_partner_type==2 && conn_power_mode==3){
		  if(con==1){
                        C1_d_present = 0;
                        printk("+++++C1 C to dp PORT++++++++");
			}
          }else if(con!=0 && change!=0 && partner_usb == 0 && conn_partner_type==4 && conn_power_mode==3){
		  if(con==1){
                        C1_d_present = 0;
                        printk("+++++C1 C to dp PORT++++++++");
			}
	  }else if(con!=0 && change!=0 && flags==0)
		{
		if(con==1 && C1_d_present==1){
			C1_d_present=0;
			printk("+++++C1 data PORT plug-out++++++++");
		}
		else if(con==2 && C2_d_present==1){
			C2_d_present=0;
			printk("+++++C2 data PORT plug-out++++++++");
		}
		else
			printk("+++++plug-out,switch to C1 PORT++++++++");
	 }else
		printk("no data port change!");
	if(C1_d_present==1 && C2_d_present==0)
	{
		printk("+++++C1 PORT switch++++++++"); // switch gpio88 to C1 port;
		a = gpio_get_value(389);
		if(a == 1){
		gpio_set_value(389,0);
		mdelay(10);
		}
		a = gpio_get_value(389);
		printk("set gpio88,con == 1,a=%d\n",a);
	} else if(C1_d_present==0 && C2_d_present==1)
	{
		printk("+++++C2 PORT switch++++++++"); // switch gpio88 to C2 port;
		a = gpio_get_value(389);
		if(a == 0){
		gpio_set_value(389,1);
		mdelay(50);
		}
		a = gpio_get_value(389);
		printk("set gpio88,con == 2,a=%d\n",a);
	} else if(C1_d_present==1 && C2_d_present==1)
	{
		printk("+++++C1 C2 PORT were both persist++++++++");
		a = gpio_get_value(389);
		if(a == 1){
		gpio_set_value(389,0);
		mdelay(10);
		}
		a = gpio_get_value(389);
		printk("set gpio88,a=%d\n",a);
	} else
	{
		printk("+++++C1 C2 PORT were not persist++++++++"); // switch gpio88 to C1 port;
		//a = gpio_get_value(389);
		//if(a == 1){
		//gpio_set_value(389,0);
		//mdelay(10);
		//}
		//a = gpio_get_value(389);
		//printk("set gpio88,a=%d\n",a);
	}


 return C1_d_present|(C2_d_present<<1)|(gpio_state<<2);
}
static int run_candidate(int con,int change,int partner_usb,int conn_partner_type,int conn_power_mode,int flags,int initial,int gpio){
 int a=0;C1_d_present=initial&1;C2_d_present=(initial>>1)&1;gpio_state=gpio;
	if(con!=0 && change!=0 && partner_usb == 1&&(conn_partner_type==1||conn_partner_type==2)&&(conn_power_mode==4||conn_power_mode==1||
		 conn_power_mode==UCSI_CONSTAT_PWR_OPMODE_TYPEC3_0))
	{
		if(con==1){
			C1_d_present = 1;
			printk("+++++C1 data PORT++++++++");
				}
		else if (con==2){
			C2_d_present = 1;
			printk("+++++C2 data PORT++++++++");
				}
		else
			printk("++++++No data port+++++++");
	  }else if((con!=0 && change!=0 && partner_usb == 1 && conn_partner_type==1 && conn_power_mode==3) ||
		(con!=0 && change!=0 && partner_usb == 1 && conn_partner_type==0 && conn_power_mode==4)){
		  //c to c connected PC
                if(con==1){
                        C1_d_present = 1;
                        printk("+++++C1 data PORT++++++++");
                                }
                else if (con==2){
                        C2_d_present = 1;
                        printk("+++++C2 data PORT++++++++");
                                }
                else
                        printk("++++++No data port+++++++");
          }else if(con!=0 && change!=0 && partner_usb == 1 && conn_partner_type==4 && (conn_power_mode==3||conn_power_mode==4)){
		if(con==1){
			C1_d_present = 1;
			printk("+++++C1 data PORT++++++++");
				}
		else if (con==2){
			C2_d_present = 1;
			printk("+++++C2 data PORT++++++++");
				}
		else
			printk("++++++No data port+++++++");
          }else if(con!=0 && change!=0 && partner_usb == 1 && conn_partner_type==2 && conn_power_mode==3){
		  if(con==1){
                        C1_d_present = 0;
                        printk("+++++C1 C to dp PORT++++++++");
			}
          }else if(con!=0 && change!=0 && partner_usb == 0 && conn_partner_type==4 && conn_power_mode==3){
		  if(con==1){
                        C1_d_present = 0;
                        printk("+++++C1 C to dp PORT++++++++");
			}
	  }else if(con!=0 && change!=0 && flags==0)
		{
		if(con==1 && C1_d_present==1){
			C1_d_present=0;
			printk("+++++C1 data PORT plug-out++++++++");
		}
		else if(con==2 && C2_d_present==1){
			C2_d_present=0;
			printk("+++++C2 data PORT plug-out++++++++");
		}
		else
			printk("+++++plug-out,switch to C1 PORT++++++++");
	 }else
		printk("no data port change!");
	if(C1_d_present==1 && C2_d_present==0)
	{
		printk("+++++C1 PORT switch++++++++"); // switch gpio88 to C1 port;
		a = gpio_get_value(389);
		if(a == 1){
		gpio_set_value(389,0);
		mdelay(10);
		}
		a = gpio_get_value(389);
		printk("set gpio88,con == 1,a=%d\n",a);
	} else if(C1_d_present==0 && C2_d_present==1)
	{
		printk("+++++C2 PORT switch++++++++"); // switch gpio88 to C2 port;
		a = gpio_get_value(389);
		if(a == 0){
		gpio_set_value(389,1);
		mdelay(50);
		}
		a = gpio_get_value(389);
		printk("set gpio88,con == 2,a=%d\n",a);
	} else if(C1_d_present==1 && C2_d_present==1)
	{
		printk("+++++C1 C2 PORT were both persist++++++++");
		a = gpio_get_value(389);
		if(a == 1){
		gpio_set_value(389,0);
		mdelay(10);
		}
		a = gpio_get_value(389);
		printk("set gpio88,a=%d\n",a);
	} else
	{
		printk("+++++C1 C2 PORT were not persist++++++++"); // switch gpio88 to C1 port;
		//a = gpio_get_value(389);
		//if(a == 1){
		//gpio_set_value(389,0);
		//mdelay(10);
		//}
		//a = gpio_get_value(389);
		//printk("set gpio88,a=%d\n",a);
	}


 return C1_d_present|(C2_d_present<<1)|(gpio_state<<2);
}
int main(void){
 assert(run_original(2,1,1,1,5,0x202d,0,0)==0);
 assert(run_candidate(2,1,1,1,5,0x202d,0,0)==6);
 assert(run_original(1,1,1,1,5,0x202d,0,1)==4);
 assert(run_candidate(1,1,1,1,5,0x202d,0,1)==1);
 int cases=0,unchanged=0,changed=0;
 for(int con=0;con<=2;con++)for(int change=0;change<=1;change++)
 for(int usb=0;usb<=1;usb++)for(int type=0;type<=6;type++)
 for(int power=0;power<=7;power++)for(int raw=0;raw<=1;raw++)
 for(int state=0;state<4;state++)for(int gpio=0;gpio<=1;gpio++){
  int flags=raw?((type<<13)|(usb?0x20:0)|power|8):0;
  int a=run_original(con,change,usb,type,power,flags,state,gpio);
  int z=run_candidate(con,change,usb,type,power,flags,state,gpio);
  int allowed=con!=0&&change!=0&&usb==1&&(type==1||type==2)&&power==5;
  if(!allowed){assert(a==z);unchanged++;}
  if(a!=z)changed++;
  cases++;
 }
 printf("{\"passed\":true,\"cases\":%d,\"unaffected_cases_equal\":%d,\"changed_cases\":%d,\"original_typec3_connector2_routes_wrong_reproduced\":true,\"candidate_routes_connector2_correctly\":true,\"other_modes_dp_otg_priority_preserved\":true}\n",cases,unchanged,changed);
 return 0;}
