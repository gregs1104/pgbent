#!/usr/bin/env python3

"""
metview.py generates metrics graphs out of a pgbent benchmark results
database.  This is the successor to the osm-metrics.py example code.

This code is at rough works for me quality with a minimal UI.
Committing and releasing in this state as a safety net to enable
refactoring toward a proper CLI tool.
"""

import argparse
import os
import matplotlib.pyplot as plt
import matplotlib.image as image
from matplotlib.offsetbox import (OffsetImage, AnnotationBbox)
from matplotlib.ticker import ScalarFormatter
import pandas as pd
import psycopg2
import psycopg2.extras

# Expand to avoid error:
#   "OverflowError: In draw_path: Exceeded cell block limit"
plt.rcParams['agg.path.chunksize'] = 10000

def format_yaxis_plain(ax):
    """Always show plain decimal Y tick labels (never scientific notation)."""
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    ax.yaxis.set_major_formatter(formatter)

def connect(options):
    # TODO Put database connection parameters into options
    conn_string = "host='localhost' dbname='results' user='gsmith' password='secret'"
    print("Connecting to database\n	->%s" % (conn_string))
    return psycopg2.connect(conn_string)

def parse():
    parser = argparse.ArgumentParser(description='metview.py benchmark results metrics viewer')
    parser.add_argument("server", help="server name",nargs='?',default='twilight')
    parser.add_argument("test", type=int, help='Test number',nargs='?',default=2568)
    return vars(parser.parse_args())

def images_dir(options):
    server=options['server']
    test=str(options['test'])
    # TODO Deal with output to server/test directory given some are missing
    base=os.path.join("results","images")
    try:
        os.mkdir(base)
    except:
        # TODO catch real errors, continue to ignore directory already exists error
        pass
    return base

def gen_label(options,df):
    server=options['server']
    test=options['test']

    # Extract run metadata from first row
    cpu=df.iloc[0]['server_cpu']
    clients=df.iloc[0]['clients']
    db_gb=round(df.iloc[0]['db_gb'])
    script=df.iloc[0]['script'].upper()

    try:
        rate_limit=round(df.iloc[0]['rate_limit'])
    except:
        rate_limit=round(df.iloc[0]['tps'])

    if rate_limit>0:
        view_label=cpu+" "+script+" "+str(db_gb)+"GB "+str(clients)+" clients @ "+str(rate_limit)+" TPS"
    else:
        view_label=cpu+" "+script+" "+str(db_gb)+"GB "+str(clients)+" clients"

    return view_label

def gen_file_name(base,view,server,test):
    unslashed=view.replace("/","-")
    name=os.path.join(base,server+"-"+str(test)+"-"+unslashed)
    return name

def gen_sql(options,dbagg):
    server=options['server']
    test=options['test']

    # TODO Use SQL injection proof parameter substitution here instead of Python's?
    sql="""
    SELECT
      --test_metrics_data.server,
      t.server_cpu AS server_cpu,
      script,
      tps,
      --scale,
      round(dbsize / (1024*1024*1024)) as db_gb,
      clients,
      rate_limit,
      CASE WHEN mi.prefix='disk' THEN split_part(d.metric,'_',1) ELSE '' END AS disk,
      CASE WHEN mi.metric_label IS null THEN d.metric ELSE mi.metric_label END AS metric,
      mi.units,
      mi.category AS cat,
      mi.visibility AS vis,
      date_trunc('%s',d.collected) AS collected,
      CASE WHEN mi.multi IS null THEN min(d.value) ELSE min(d.value * mi.multi) END AS min,
      CASE WHEN mi.multi IS null THEN avg(d.value) ELSE avg(d.value * mi.multi) END AS avg,
      CASE WHEN mi.multi IS null THEN max(d.value) ELSE max(d.value * mi.multi) END AS max
      FROM
        tests t,test_metrics_data d
      LEFT OUTER JOIN metrics_info mi ON
        (d.metric=mi.metric OR (mi.prefix='disk' AND d.metric LIKE ('%%' || mi.metric)))
      WHERE
        d.server=t.server AND
        d.test=t.test AND
        (mi.uname=t.uname OR mi.uname IS null OR mi.uname='Database') AND
        d.test=%s AND
        d.server='%s'
    GROUP BY d.server,t.server_cpu,script,t.scale,clients,rate_limit,tps,round(dbsize / (1024*1024*1024)),d.metric,mi.prefix,mi.metric_label,mi.units,mi.category,mi.multi,mi.visibility,date_trunc('%s',collected)
    ORDER BY d.server,t.server_cpu,script,t.scale,clients,rate_limit,round(dbsize / (1024*1024*1024)),d.metric,mi.prefix,mi.metric_label,mi.units,mi.category,mi.multi,mi.visibility,date_trunc('%s',collected)
    ;""" % (dbagg,test,server,dbagg,dbagg)

    return sql

def query_multi_met(options):
    # TODO determine dbagg based on length of test run
    dbagg='second'

    sql=gen_sql(options, dbagg)
    print ("sql=",sql)
    return sql

def query_single_met(options):
    # TODO determine dbagg based on length of test run
    dbagg='second'

    sql=gen_sql(options, dbagg)
    print ("sql=",sql)
    return sql

def graph_single(options,df):
    server=options['server']
    test=options['test']

    metrics={}
    rendered=0

    base=images_dir(options)

    plt.rcParams.update({'font.size':'18'})
    colors=('green','blue','purple')

    logo_file="reports/Color Horizontal.jpg"
    logo=image.imread(logo_file)
    logo_im = OffsetImage(logo, zoom=.03)

    ylabel="TPS"

    g=df.groupby(['metric'])

    for k,v in g:
        print("Processing",k)
        print(v)
        metrics[k]=v
        v.set_index('collected',inplace=True)

        view_label=gen_label(options,df)

        # TODO put k into generated label
        units=v['units'][0]
        ylabel=units

        metrics[k]=metrics[k].drop(columns=['avg','metric'])
        metrics[k].rename(columns={'max': k}, inplace=True)

        ax=v['avg'].plot(rot=90,title=view_label,figsize=(8,6))
        #,color=colors[rendered])

        # TODO This just shows avg/avg/avg on legend, should be min/avg/max
        #ax.legend()

        ax.set_ylabel(ylabel)
        ax.grid(True,which='both')
        format_yaxis_plain(ax)

        fn=gen_file_name(base,k,server,test)
        # TODO Bottom part of graph is strangely cut off?  Rotation issue?
        plt.savefig(fn,dpi=600)  # 80 for =640x480 figures
        print("saved to '%s.png'" % fn)

        ab = AnnotationBbox(logo_im, (1, 0), frameon=False, xycoords='axes fraction',
             box_alignment=(0.55,1.85))
        ax.add_artist(ab)
        plt.savefig(fn+"-logo",dpi=600)  # 80 for =640x480 figures
        print("saved to '%s-logo.png'" % fn)
        plt.clf()

# This function combines multiple metrics onto a shared Y axis
def graph_group(options,df):
    server=options['server']
    test=options['test']

    metrics={}
    rendered=0

    base=images_dir(options)

    plt.rcParams.update({'font.size':'18'})
    colors=('green','blue','purple')

    logo_file="reports/Color Horizontal.jpg"
    logo=image.imread(logo_file)
    logo_im = OffsetImage(logo, zoom=.03)

    view_set=['min_latency','max_latency','avg_latency']
    ylabel="Latency (ms)"
    view_label='Latency '+str(test)

    g=df.groupby(['cat','units','metric'])

    for k,v in g:
        print("Processing",k)
        print(v)
        metrics[k]=v
        v.set_index('collected',inplace=True)

        metrics[k]=metrics[k].drop(columns=['avg','metric'])
        metrics[k].rename(columns={'max': k}, inplace=True)

        if k in view_set:
            rendered=rendered+1

            ax=v['avg'].plot(rot=90,title=view_label,figsize=(8,6))
            #,color=colors[rendered])

            # TODO This just shows avg/avg/avg on legend, should be min/avg/max
            #ax.legend()

            ax.set_ylabel(ylabel)
            ax.grid(True,which='both')

            fn=gen_file_name(base,k,server,test)
            # Only save on last metric in the view list
            if rendered==(len(view_set)):
                # TODO Bottom part of graph is strangely cut off?  Rotation issue?
                plt.savefig(fn,dpi=600)  # 80 for =640x480 figures
                print("saved to '%s.png'" % fn)

                ab = AnnotationBbox(logo_im, (1, 0), frameon=False, xycoords='axes fraction',
                     box_alignment=(0.55,1.85))
                ax.add_artist(ab)
                plt.savefig(fn+"-logo",dpi=600)  # 80 for =640x480 figures
                print("saved to '%s-logo.png'" % fn)

# TODO add options to change which query and graph function are called
def graph(options,conn):
    try:
        sql=query_single_met(options)
        print(sql)
        df = pd.read_sql_query(sql, conn)
        print(df)
        graph_single(options,df)
    finally:
        conn.close()

def gen_graphs():
    args_dict=parse()
    c=connect(args_dict)
    graph(args_dict,c)

if __name__ == "__main__":
    gen_graphs()
