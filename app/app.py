import streamlit as st 
import glob
import pandas as pd
import os, time, re

# oneflux wrapper and processing loop
def oneflux_processing(tb, my_bar):

    # grab state variables, i.e. processing
    # parameters set by the interface
    processing = st.session_state.choice
    threshold = st.session_state.slider
    
    # forced overwrite
    if st.session_state.checkbox:
        forced = "--force-py"
    else:
        forced = ""
    
    # set increment of progress bar
    increment = 100/tb.shape[0]
    
    for index, row in tb.iterrows():
        
        # these are demos and won't really cover all possible settings
        # different products are not listed for the --prod parameter
        if processing == "all (full pipeline)":
            st.write("test")
            cmd = "cd /ONEFlux/; python runoneflux.py all " + data_dir + " " + \
            row["site"] + " " + \
            row["path"] + " " + \
            row["start_year"]  + " " + \
            row["end_year"]  + " " + \
            "-l fluxnet_pipeline.log --mcr /opt/mcr/v94/ --recint hh"
        
        if processing == "daytime partinioning":
            cmd = "cd /ONEFlux/; python runoneflux.py partition_dt " + data_dir + " " + \
            row["site"] + " " + \
            row["path"] + " " + \
            row["start_year"] + " " + \
            row["end_year"] + " " + \
            "-l fluxnet_partition_dt.log" + " " + \
            "--prod y" + " " + \
            "--perc " + threshold + " " + forced
            
        if processing == "nighttime partinioning":
            cmd = "cd /ONEFlux/; python runoneflux.py partition_nt " + data_dir + " " + \
            row["site"] + " " + \
            row["path"] + " " + \
            row["start_year"] + " " + \
            row["end_year"] + " " + \
            "-l fluxnet_partition_nt.log"      
        
        # run command and retain exit code value
        value = os.system(cmd)
        
        # check if the site processed cleanly
        if value == 0:
            tb.loc[index, "status"] = "processed"        
        
        # progress bar increment
        my_bar.progress(int((index + 1) * increment))
        st.dataframe(tb)

if __name__ == '__main__':
    
    # Sidebar
    st.sidebar.title("ONEFlux Docker App")
    st.sidebar.markdown(
        "This is a quick app to process the flux \
        data in a docker container. Please select \
        your presets and hit the 'process data' button. \
        By default previous data are overwritten. For \
        automated processing see the headless version of \
        this container."
    )

    force = st.sidebar.checkbox(
        "Overwrite existing results",
         value = True,
         key = "checkbox"
    )

    # Main layout
    # recursively find all qcv files
    # extract the fluxnet acronym
    # and years (assuming that all files
    # will be formatted as such)
    data_dir = "/data"
    regex = re.compile('((?P<name>qcv_)\d\d\d\d.csv)')
    
    files = []
    for root, dirs, names in os.walk(data_dir):
        for file in names:
            if regex.search(file):
                filepath = root + os.sep + file
                files.append(filepath)
    
    #files = glob.glob(os.path.join(data_dir,"**/qcv_files/*qcv*.csv"))

    # wrangle the files into a table for display
    # first populate a dataframe with the basic info
    # i.e. site names, years covered, base paths
    df = pd.DataFrame(files)
    df.columns = ["file"]
    df["site"] = df["file"].map(lambda x: os.path.basename(x).split('_')[0])
    df["year"] = df["file"].map(lambda x: os.path.basename(x).split('_')[2].split('.')[0])
    df["path"] = df["file"].map(lambda x: x.split('/')[2])
    
    # summary table dplyr style groupby > mutate only supported
    # as of version 0.25.0 this setup only supports up to 0.24
    # due to python 2.7 requirements so crufty stuff it will be
    tb = df[["site","year","path"]].groupby("site").apply(
        lambda x: min(x['path'])).reset_index()
    tb.columns = ["site","path"]
    tmp = df[["site","year","path"]].groupby("site").apply(
        lambda x: min(x['year'])).reset_index()
    tmp.columns = ["site","start_year"]
    tb = tb.merge(tmp, on="site", how = "left")
    end_year = df[["site","year","path"]].groupby("site").apply(
        lambda x: max(x['year'])).reset_index()
    tmp.columns = ["site","end_year"]
    tb = tb.merge(tmp, on="site", how = "left")
    tmp = df[["site","year","path"]].groupby("site").apply(
        lambda x: len(x['year'])).reset_index()
    tmp.columns = ["site","site_years"]
    tb = tb.merge(tmp, on="site", how = "left")
    tb["status"] = "unprocessed"

    # the header columns with selectable variables
    #colh1, colh2, colh3 = st.columns(3)
    choices = ["all (full pipeline)","nighttime partitioning","daytime partitioning"]
        
    # dynamic items
    partitioning = st.selectbox(
        "Select flux processing",
         choices,
         key = "choice"
    )
    
    threshold = st.slider(
        "USTAR percentile threshold (if applicable)", 0, 100, 50,
        key = "slider"
    )
    
    # Some dashboard metrics
    #col1, col2 = st.columns(2)
    #col1.metric("Total Sites", tb.shape[0])
    #col2.metric("Total site years", tb["site_years"].sum())
       
    #st.session_state.progress = 0
    my_bar = st.progress(0)

    # use st.empty() to update
    # the rendered table and in particular
    # the process status
    with st.empty():
        
        # summary table element
        st.dataframe(tb)
        
        # process data upon click and update table
        # and stats
        if st.button('Process data'):
            tb_update = oneflux_processing(tb, my_bar)

