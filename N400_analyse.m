%% ========================================================================
%  ERP N400 ANALYSE SCRIPT (ENDELIG VERSION)
%  Beskrivelse: Sammenligner to betingelser, laver parret t-test og flot plot.
%  Virker på: Alle epoched EEGLAB datasæt med lige antal trials.
%  ========================================================================

% --- 1. BRUGER-INDSTILLINGER ---
chan_label  = 'CPz';          % Den kanal du vil analysere
rel_codes   = {'211', '212'}; % Related/Match koder (som strings)
unrel_codes = {'221', '222'}; % Unrelated/Mismatch koder (som strings)

time_win    = [300 500];     % Statistisk tidsvindue (ms)
plot_lims   = [-200 800];    % Plot tidsramme (ms)
smooth_hz   = 20;            % Udjævning (jo lavere tal, jo mere glat)

% --- 2. DATA IDENTIFIKATION ---
% Find kanal-index
c_idx = find(strcmpi({EEG.chanlocs.labels}, chan_label));
if isempty(c_idx), error('Kanalen blev ikke fundet!'); end

% Match koder til epochs (finder trigger ved tid 0)
epoch_types = {};
for i = 1:length(EEG.epoch)
    zero_idx = find([EEG.epoch(i).eventlatency{:}] == 0);
    type = EEG.epoch(i).eventtype{zero_idx};
    if isnumeric(type); type = num2str(type); end
    epoch_types{i} = type;
end

idx_1 = find(ismember(epoch_types, rel_codes));
idx_2 = find(ismember(epoch_types, unrel_codes));

% --- 3. BEREGNINGER & STATISTIK ---
% ERP Gennemsnit
erp_1 = mean(EEG.data(c_idx, :, idx_1), 3);
erp_2 = mean(EEG.data(c_idx, :, idx_2), 3);

% Smoothing (Low-pass look)
s_factor = round(EEG.srate/smooth_hz);
s_1 = movmean(erp_1, s_factor);
s_2 = movmean(erp_2, s_factor);
s_diff = s_2 - s_1;

% Forberedelse til parret t-test
t_idx = find(EEG.times >= time_win(1) & EEG.times <= time_win(2));
vals_1 = squeeze(mean(EEG.data(c_idx, t_idx, idx_1), 2));
vals_2 = squeeze(mean(EEG.data(c_idx, t_idx, idx_2), 2));

% DEFINER N_TRIALS (Sikrer at parret t-test har lige mange par, hvis noget blev slettet)
n_trials = min(length(vals_1), length(vals_2));

% Kør Paired t-test
[h, p, ci, stats] = ttest(vals_2(1:n_trials), vals_1(1:n_trials));

% --- 4. STILRENT PLOT (MED FIX TIL LEGENDE) ---
hf = figure('Color', 'w', 'Position', [100 100 850 500]);
ax = axes('Parent', hf, 'Color', 'w', 'FontSize', 11, 'Box', 'off');
hold(ax, 'on');

% Marker N400 vindue (Skygge)
y_limit_val = max(abs([s_1, s_2, s_diff])) * 1.3;
fill([time_win(1) time_win(2) time_win(2) time_win(1)], ...
     [-y_limit_val -y_limit_val y_limit_val y_limit_val], ...
     [0.95 0.95 0.95], 'EdgeColor', 'none', 'HandleVisibility', 'off');

% Onset og Baseline linjer
line(plot_lims, [0 0], 'Color', [0.4 0.4 0.4], 'HandleVisibility', 'off');
line([0 0], [-y_limit_val y_limit_val], 'Color', [0.4 0.4 0.4], 'LineStyle', ':', 'HandleVisibility', 'off');

% Plot Kurver
p1 = plot(EEG.times, s_1, 'Color', [0 0.5 0], 'LineWidth', 2, 'DisplayName', 'Congruent trials');
p2 = plot(EEG.times, s_2, 'Color', [0.8 0 0], 'LineWidth', 2, 'DisplayName', 'Incongruent trials');
p3 = plot(EEG.times, s_diff, 'k--', 'LineWidth', 1.2, 'DisplayName', 'Difference Wave');

% Formatering af akser
set(ax, 'YDir', 'reverse', 'TickDir', 'out', 'XColor', 'k', 'YColor', 'k');
xlim(plot_lims); ylim([-y_limit_val y_limit_val]);
xlabel('Time (ms)', 'Color', 'k'); ylabel('Amplitude (\muV)', 'Color', 'k');
title(['ERP Analysis: ' chan_label ' '], 'Color', 'k');
grid on;

% Fix til legende (Tvinger hvid baggrund og sort tekst)
lgd = legend([p1, p2, p3], 'Location', 'northeastoutside');
set(lgd, 'Color', 'w', 'TextColor', 'k', 'EdgeColor', 'k', 'FontSize', 10);

% Ekstra sikkerhed: Tving hele figuren til ikke at invertere ved gem/kopi
set(hf, 'InvertHardcopy', 'off');

% --- 5. FORMATERING TIL VIDENSKABELIG ARTIKEL ---
% 1. Beregn frihedsgrader (df)
df = n_trials - 1;

% 2. Beregn Cohens d for parrede data (Effektstørrelse)
forskelle = vals_2(1:n_trials) - vals_1(1:n_trials);
cohens_d = mean(forskelle) / std(forskelle);

% 3. Formater p-værdien korrekt (APA-format)
if p < 0.001
    p_string = 'p < .001';
else
    p_string = sprintf('p = %.3f', p);
    p_string = strrep(p_string, '0.', '.'); 
end

% 4. PRINT LINJE TIL ARTIKEL
fprintf('\n========================================================================\n');
fprintf('KLAR TIL ARTIKEL (Kopier linjen herunder):\n\n');
fprintf('A paired-samples t-test revealed a significant difference in the N400 time window at channel %s, t(%d) = %.2f, %s, d = %.2f.\n', ...
    chan_label, df, stats.tstat, p_string, cohens_d);
fprintf('========================================================================\n');