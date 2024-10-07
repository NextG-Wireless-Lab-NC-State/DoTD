%=======================================================================================
Current_Cmax = 0; Current_Lmax = 0; % Initialize the current maximum of capacity and latency
LTSR = zeros(1,length(sat)); % Long-term score return
ST_LTSR = zeros(1,length(sat)); % Long-term score return
G_LTSR = zeros(1,length(sat)); % Long-term score return
Distance_stat = zeros(length(sat),length(sat));
Total_Score = zeros(length(sat),length(sat));
ST_Total_Score = zeros(length(sat),length(sat));
Gamma = 1; % Discount Factor
w1 = 0.45; % Weight of objective function
w2 = 0.5; % Weight of objective function
Timesec = 400; % in [sec]
Num_Timstep = 1000;
Total_Capacity = zeros(1,Num_Timstep);
LTSR_Data = zeros(1,Num_Timstep);
ST_LTSR_Data = zeros(1,Num_Timstep);
G_LTSR_Data = zeros(1,Num_Timstep);
Cap_opt_link = zeros(1,length(sat));
ST_Cap_opt_link = zeros(1,length(sat));
G_Cap_opt_link = zeros(1,length(sat));
Avr_Latency = zeros(1,Num_Timstep);
ST_Total_Capacity = zeros(1,Num_Timstep);
G_Total_Capacity = zeros(1,Num_Timstep);
ST_Avr_Latency = zeros(1,Num_Timstep);
G_Avr_Latency = zeros(1,Num_Timstep);
%---------------------------------------------------------------------------------------
Total_Link_Churn = zeros(1,Num_Timstep);
ST_Total_Link_Churn = zeros(1,Num_Timstep);
G_Total_Link_Churn = zeros(1,Num_Timstep);
Link_Churn = zeros(1,length(sat));
ST_Link_Churn = zeros(1,length(sat));
G_Link_Churn = zeros(1,length(sat));
Laten_opt_link = zeros(1,length(sat));
ST_Laten_opt_link = zeros(1,length(sat));
G_Laten_opt_link = zeros(1,length(sat));
%---------------------------------------------------------------------------------------
Pre_Optimal_link_selection = zeros(length(sat),length(sat)); % Initialize the optimal link selections for DP
ST_Pre_Optimal_link_selection = zeros(length(sat),length(sat)); % Initialize the optimal link selections for ST
Pre_Optimal_link_selection_grid = zeros(length(sat),length(sat)); % Initialize the optimal link selections for Grid
%---------------------------------------------------------------------------------------
Save_Opt_Link = zeros(length(sat),length(sat),Num_Timstep);
ST_Save_Opt_Link = zeros(length(sat),length(sat),Num_Timstep);
G_Save_Opt_Link = zeros(length(sat),length(sat),Num_Timstep);
Save_Capacity = zeros(length(sat),length(sat),Num_Timstep);
Save_Latency = zeros(length(sat),length(sat),Num_Timstep);
%---------------------------------Loop---------------------------------------------------
for time_step = 1:Num_Timstep
    %------------------------------------------------------------------------------------
    Optimal_link_selection = zeros(length(sat),length(sat));    % Initialize the optimal link selections for DP
    ST_Optimal_link_selection = zeros(length(sat),length(sat)); % Initialize the optimal link selections for ST
    %Optimal_link_grid = zeros(length(sat),length(sat)); % Initialize the optimal link selections for +Grid
    Optimal_Same_Orbit_Link = zeros(length(sat),length(sat)); % Initialize the optimal link selections for +Grid
    %------------------------------------------------------------------------------------
    [Year, Month, Day, Hour, Minute, Second] = DateTimeUpdate(Year, Month, Day, Hour, Minute,Second,Timesec);
    time = datetime(Year, Month, Day, Hour, Minute, Second); % (Year, Month, Day, Hour, Minute, Second)
    for i = 1:length(sat)
        [az,elev,r] = aer(sat(i),sat,time); Distance_stat(i,:) = r'; % Distance between i-th satellite to all satellites
    end
    %------------------------------------------------------------------------------------
    Link_Connect = (Distance_stat <= Max_Distance).*(1-eye(length(sat),length(sat)));   
    Latency = (Link_Connect.*Distance_stat)/Prop_delay; % Propagation delay [sec] 
    %----------------------Free Spacce Path Loss-----------------------------------------
    %fspl = (20*log10(Distance_stat/1000)) + 20*log10(channelFreq_isls) + 92.45;
    fspl = (20*log10(Distance_stat)) + 20*log10(channelFreq_isls*1e9) - 147.55;
    %----------------------Satellite Channel Gain -------------------------
    rss_dBm = satellite_eirp - 2 + satellite_receive_attenna_gain - fspl - polarization_loss - misalignment_attenuation_losses - 1.0;
    %----------------------Receive signal power -----------------------------------------
    rss_watt = power(10,(rss_dBm - 30)/10); 
    %----------------------Noise power --------------------------------------------------
    noise_watt = 200*1.38064852*power(10,-23)*channel_bandwidth*power(10,6);
    %----------------------SNR-----------------------------------------------------------
    snr = rss_watt/noise_watt;
    %----------------------Networks Capacity---------------------------------------------
    Capacity = (channel_bandwidth.*log2(1+snr)/power(10,6));     % Capacity in [Gbps]
    Capacity(isinf(Capacity)) = 0;
    %------------------------------------------------------------------------------------
    %                      Dynamic Programming Algorithm
    %------------------------------------------------------------------------------------
    %----------------------Compute Max Capacity and Latency------------------------------
    Cmax = max([max(max(Capacity)),Current_Cmax]); Current_Cmax = Cmax;
    %------------------------------------------------------------------------------------
    Lmax = max([max(max(Latency)),Current_Lmax]); Current_Lmax = Lmax;
    %------------------------------------------------------------------------------------
    for k = 1:length(sat)
        %--------------------------------------------------------------------------------
        Obj_cap = Link_Connect(k,:).*Capacity(k,:)/Cmax;
        Obj_Laten = Link_Connect(k,:).*(1-(Latency(k,:)/Lmax));
        Obj_LChurn = Link_Connect(k,:).*Pre_Optimal_link_selection(k,:)/Number_Links_Selection;
        ST_Obj_LChurn = Link_Connect(k,:).*ST_Pre_Optimal_link_selection(k,:)/Number_Links_Selection;
        %-------------------------------------------------------------------------------
        Total_Score(k,:) = (w1*Obj_cap) + (w2*Obj_Laten) + ((1-w1-w2)*Obj_LChurn) + (Link_Connect(k,:).*LTSR);
        %-------------------------------------------------------------------------------
        ST_Total_Score(k,:) = (w1*Obj_cap) + (w2*Obj_Laten) + ((1-w1-w2)*ST_Obj_LChurn);
        %-------------------------------------------------------------------------------
    end
    %----------------------Select the optimal links--------------------------------------
    [Optimal_link_selection] = Optimal_link_selections(Total_Score,Optimal_link_selection,Number_Links_Selection,Link_Connect);
    [ST_Optimal_link_selection] = Optimal_link_selections(ST_Total_Score,ST_Optimal_link_selection,Number_Links_Selection,Link_Connect);
    %----------------------Optimal links for +Grid---------------------------------------
    Same_Orbit_Opt_Link = Link_Connect.*Same_Orbit_Ind; %
    Score_Same_orbit = Same_Orbit_Opt_Link.*Distance_stat;
    Score_Same_orbit(find(Score_Same_orbit==0)) = Inf;
    Optimal_Same_Orbit_Link = Optimal_link_Grid(Score_Same_orbit,Optimal_Same_Orbit_Link,Number_Links_Selection-Number_Links_Grid,Same_Orbit_Opt_Link);
    %------------------------------------------------------------------------------------
    for m = 1:length(sat)
        [az,elev,Left_Ditance] = aer(sat(m),sat(find(Left_SameOrbit(m,:))),time);
        Left_Node_Ind = find(Left_SameOrbit(m,:)); Left_Node = Left_Node_Ind(find(Left_Ditance == min(Left_Ditance)));
        %-ST_Optimal_link_selection-------------------------------------------------------------------------
        [az,elev,Right_Ditance] = aer(sat(m),sat(find(Right_SameOrbit(m,:))),time);
        Right_Node_Ind = find(Right_SameOrbit(m,:)); Right_Node = Right_Node_Ind(find(Right_Ditance == min(Right_Ditance)));
        %------------------------------Left------------------------------------
        if (sum(LeftRightInd(m,:)) < 2) && (sum(LeftRightInd(Left_Node(1),:)) < 2) && (sum(LeftInd(m,:)) < 1) && (sum(LeftInd(Left_Node(1),:)) < 1)
            LeftRightInd(m,Left_Node(1)) = 1; LeftRightInd(Left_Node(1),m) = 1;
            LeftInd(m,Left_Node(1)) = 1; LeftInd(Left_Node(1),m) = 1;
        end
        %------------------------------Right-----------------------------------
        if (sum(LeftRightInd(m,:)) < 2) && (sum(LeftRightInd(Right_Node(1),:)) < 2) && (sum(RightInd(m,:)) < 1) && (sum(RightInd(Right_Node(1),:)) < 1)
            LeftRightInd(m,Right_Node(1)) = 1; LeftRightInd(Right_Node(1),m) = 1;
            RightInd(m,Right_Node(1)) = 1; RightInd(Right_Node(1),m) = 1;
        end
    end
    Optimal_link_grid = RightInd | LeftInd;
    %---------------------------------------------------------------------------
    Optimal_link_selection_grid = (Optimal_link_grid | Optimal_Same_Orbit_Link); % Optimal link Selections for +Grid
    %----------------------Save Optimal Links and KPMs-----------------------------------
    Save_Opt_Link(:,:,time_step) = Optimal_link_selection;
    ST_Save_Opt_Link(:,:,time_step) = ST_Optimal_link_selection;
    G_Save_Opt_Link(:,:,time_step) = Optimal_link_selection_grid;
    Save_Capacity(:,:,time_step) = Capacity; Save_Latency(:,:,time_step) = Latency;
    %----------------------Perforamnces Evaluations--------------------------------------
    LTSR_PRE = LTSR; ST_LTSR_PRE = ST_LTSR; G_LTSR_PRE = G_LTSR; 
    Cap_opt_link_pre = Cap_opt_link; ST_Cap_opt_link_pre = ST_Cap_opt_link; G_Cap_opt_link_pre = G_Cap_opt_link;
    Laten_opt_link_pre = Laten_opt_link; ST_Laten_opt_link_pre = ST_Laten_opt_link; G_Laten_opt_link_pre = G_Laten_opt_link;
    Link_Churn_pre = Link_Churn; ST_Link_Churn_pre = ST_Link_Churn; G_Link_Churn_pre = G_Link_Churn;
    %------------------------------------------------------------------------------------
    Laten_opt_link = zeros(1,length(sat)); ST_Laten_opt_link = zeros(1,length(sat)); G_Laten_opt_link = zeros(1,length(sat));
    %------------------------------------------------------------------------------------
    for k = 1:length(sat)
        Coef = sum(Optimal_link_selection(k,:)); ST_Coef = sum(ST_Optimal_link_selection(k,:)); 
        G_Coef = sum(Optimal_link_selection_grid(k,:));
        %-------------------------------------------------------------------------------
        Obj_cap = Optimal_link_selection(k,:).*Capacity(k,:)/Cmax;
        Obj_Laten = Optimal_link_selection(k,:).*(1-(Latency(k,:)/Lmax)); 
        Obj_LChurn = Optimal_link_selection(k,:).*Pre_Optimal_link_selection(k,:)/Number_Links_Selection;
        %-------------------------------------------------------------------------------
        ST_Obj_cap = ST_Optimal_link_selection(k,:).*Capacity(k,:)/Cmax;
        ST_Obj_Laten = ST_Optimal_link_selection(k,:).*(1-(Latency(k,:)/Lmax)); 
        ST_Obj_LChurn = ST_Optimal_link_selection(k,:).*ST_Pre_Optimal_link_selection(k,:)/Number_Links_Selection;
        %-------------------------------------------------------------------------------
        G_Obj_cap = Optimal_link_selection_grid(k,:).*Capacity(k,:)/Cmax;
        G_Obj_Laten = Optimal_link_selection_grid(k,:).*(1-(Latency(k,:)/Lmax)); 
        G_Obj_LChurn = Optimal_link_selection_grid(k,:).*Pre_Optimal_link_selection_grid(k,:)/Number_Links_Selection;
        %------------------Long-term score return----------------------------------------
        LTSR(k) = sum((w1*Obj_cap) + (w2*Obj_Laten) + ((1-w1-w2)*Obj_LChurn) + (Optimal_link_selection(k,:).*LTSR_PRE))/Number_Links_Selection;
        %--------------------------------------------------------------------------------
        ST_LTSR(k) = sum((w1*ST_Obj_cap) + (w2*ST_Obj_Laten) + ((1-w1-w2)*ST_Obj_LChurn) + (ST_Optimal_link_selection(k,:).*ST_LTSR_PRE))/Number_Links_Selection;
        %--------------------------------------------------------------------------------
        G_LTSR(k) = sum((w1*G_Obj_cap) + (w2*G_Obj_Laten) + ((1-w1-w2)*G_Obj_LChurn) + (Optimal_link_selection_grid(k,:).*G_LTSR_PRE))/Number_Links_Selection;
        %------------------Total capacity------------------------------------------------
        Cap_opt_link(k) = sum(Obj_cap + (Optimal_link_selection(k,:).*Cap_opt_link_pre))/Number_Links_Selection;
        ST_Cap_opt_link(k) = sum(ST_Obj_cap  + (ST_Optimal_link_selection(k,:).*ST_Cap_opt_link_pre))/Number_Links_Selection;
        G_Cap_opt_link(k) = sum(G_Obj_cap  + (Optimal_link_selection_grid(k,:).*G_Cap_opt_link_pre))/Number_Links_Selection;
        %------------------Latency-------------------------------------------------------
        if (Coef>0) && (ST_Coef>0) && (G_Coef>0)
            Laten_opt_link(k) = sum(Obj_Laten + (Optimal_link_selection(k,:).*Laten_opt_link_pre))/Coef;
            ST_Laten_opt_link(k) = sum(ST_Obj_Laten + (ST_Optimal_link_selection(k,:).*ST_Laten_opt_link_pre))/ST_Coef;
            G_Laten_opt_link(k) = sum(G_Obj_Laten + (Optimal_link_selection_grid(k,:).*G_Laten_opt_link_pre))/G_Coef;
        end
        %------------------Link Churn----------------------------------------------------
        Link_Churn(k) = sum(Obj_LChurn + (Optimal_link_selection(k,:).*Link_Churn_pre))/Number_Links_Selection;
        ST_Link_Churn(k) = sum(ST_Obj_LChurn + (ST_Optimal_link_selection(k,:).*ST_Link_Churn_pre))/Number_Links_Selection;
        G_Link_Churn(k) = sum(G_Obj_LChurn + (Optimal_link_selection_grid(k,:).*G_Link_Churn_pre))/Number_Links_Selection;
    end
    % -------------------------------------Long-term score return------------------------
    LTSR_Data(time_step) = sum(LTSR)/max([1,length(find(LTSR==0))]); 
    ST_LTSR_Data(time_step) = sum(ST_LTSR)/max([1,length(find(ST_LTSR==0))]); 
    G_LTSR_Data(time_step) = sum(G_LTSR)/max([1,length(find(G_LTSR==0))]);
    %--------------------------------------Capacity--------------------------------------
    Total_Capacity(time_step) = sum(Cap_opt_link)/max([1,length(find(Cap_opt_link==0))]); 
    ST_Total_Capacity(time_step) = sum(ST_Cap_opt_link)/max([1,length(find(ST_Cap_opt_link==0))]); 
    G_Total_Capacity(time_step) = sum(G_Cap_opt_link)/max([1,length(find(G_Cap_opt_link==0))]);
    %--------------------------------------Latency---------------------------------------
    Avr_Latency(time_step) = sum(Laten_opt_link)/max([1,length(find(Laten_opt_link==0))]); 
    ST_Avr_Latency(time_step) = sum(ST_Laten_opt_link)/max([1,length(find(ST_Laten_opt_link==0))]);
    G_Avr_Latency(time_step) = sum(G_Laten_opt_link)/max([1,length(find(G_Laten_opt_link==0))]);
    %--------------------------------------Link Churn------------------------------------
    if time_step > 1
        Total_Link_Churn(time_step) = sum(Link_Churn)/max([1,length(find(Link_Churn==0))]); 
        ST_Total_Link_Churn(time_step) = sum(ST_Link_Churn)/max([1,length(find(ST_Link_Churn==0))]); 
        G_Total_Link_Churn(time_step) = sum(G_Link_Churn)/max([1,length(find(G_Link_Churn==0))]);
    end
    %------------------------------------------------------------------------------------
    Pre_Optimal_link_selection = Optimal_link_selection;
    ST_Pre_Optimal_link_selection = ST_Optimal_link_selection;
    Pre_Optimal_link_selection_grid = Optimal_link_selection_grid;
end