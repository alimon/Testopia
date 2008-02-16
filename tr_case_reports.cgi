#!/usr/bin/perl -wT
# -*- Mode: perl; indent-tabs-mode: nil -*-
#
# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Original Code is the Bugzilla Testopia System.
#
# The Initial Developer of the Original Code is Greg Hendricks.
# Portions created by Maciej Maczynski are Copyright (C) 2006
# Novell. All Rights Reserved.
#
# Contributor(s): Greg Hendricks <ghendricks@novell.com>

# Portions taken from Bugzilla reports by Gervase Markham <gerv@gerv.net>

use strict;
use lib ".";

use Bugzilla;
use Bugzilla::Constants;
use Bugzilla::Error;
use Bugzilla::Util;
use Bugzilla::Testopia::Util;
use Bugzilla::Testopia::Constants;
use Bugzilla::Testopia::Report;

my $vars = {};
my $template = Bugzilla->template;
my $cgi = Bugzilla->cgi;

Bugzilla->login(LOGIN_REQUIRED);

my $type = $cgi->param('type') || '';

if ($type eq 'status-breakdown'){
    my $case_id = trim(Bugzilla->cgi->param('case_id') || '');
    
    unless ($case_id){
      $vars->{'form_action'} = 'tr_case_reports.cgi';
      $template->process("testopia/case/choose.html.tmpl", $vars) 
          || ThrowTemplateError($template->error());
      exit;
    }
    validate_test_id($case_id, 'case');
    
    my $case = Bugzilla::Testopia::TestCase->new($case_id);
    exit unless $case->canview;
    
    my @data;
    my $caserun = Bugzilla::Testopia::TestCaseRun->new({});
    
    my @names;
    my @values;
    foreach my $status (@{$caserun->get_status_list}){
         push @names, $status->{'name'};
         push @values, $case->get_caserun_count($status->{'id'});
    }
    push @data, \@names;
    push @data, \@values;

    $vars->{'width'} = 200;
    $vars->{'height'} = 150;
    $vars->{'data'} = \@data;
    $vars->{'chart_title'} = 'Historic Status Breakdown';
    $vars->{'colors'} = (['#858aef', '#56e871', '#ed3f58', '#b8eae1', '#f1d9ab', '#e17a56']);
    print $cgi->header;
    $template->process("testopia/reports/report-pie.png.tmpl", $vars)
       || ThrowTemplateError($template->error());
}
else{
    $cgi->param('current_tab', 'case');
    $cgi->param('viewall', 1);
    my $report = Bugzilla::Testopia::Report->new('case', 'tr_list_cases.cgi', $cgi);
    $vars->{'report'} = $report;

    ### From Bugzilla report.cgi by Gervase Markham
    my $formatparam = $cgi->param('format');
    my $report_action = $cgi->param('report_action');
    if ($report_action eq "data") {
        # So which template are we using? If action is "wrap", we will be using
        # no format (it gets passed through to be the format of the actual data),
        # and either report.csv.tmpl (CSV), or report.html.tmpl (everything else).
        # report.html.tmpl produces an HTML framework for either tables of HTML
        # data, or images generated by calling report.cgi again with action as
        # "plot".
        $formatparam =~ s/[^a-zA-Z\-]//g;
        trick_taint($formatparam);
        $vars->{'format'} = $formatparam;
        $formatparam = '';
    }
    elsif ($report_action eq "plot") {
        # If action is "plot", we will be using a format as normal (pie, bar etc.)
        # and a ctype as normal (currently only png.)
        $vars->{'cumulate'} = $cgi->param('cumulate') ? 1 : 0;
        $vars->{'x_labels_vertical'} = $cgi->param('x_labels_vertical') ? 1 : 0;
        $vars->{'data'} = $report->{'image_data'};
    }
    else {
        ThrowCodeError("unknown_action", {action => $cgi->param('report_action')});
    }
 
    my $format = $template->get_format("testopia/reports/report", $formatparam,
                                   scalar($cgi->param('ctype')));

    my @time = localtime(time());
    my $date = sprintf "%04d-%02d-%02d", 1900+$time[5],$time[4]+1,$time[3];
    my $filename = "report-" . $date . ".$format->{extension}";
    
    my $disp = "inline";
    # We set CSV files to be downloaded, as they are designed for importing
    # into other programs.
    if ( $format->{'extension'} eq "csv" || $format->{'extension'} eq "xml" ){
        $disp = "attachment";
    }

    print $cgi->header(-type => $format->{'ctype'},
                       -content_disposition => "$disp; filename=$filename");

    $vars->{'time'} = $date;
    $template->process("$format->{'template'}", $vars)
        || ThrowTemplateError($template->error());

    exit;
}
