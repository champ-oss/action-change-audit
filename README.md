# action-change-audit

Summary: using GitHub library to create a changelog from commit merges.  Make sure the merges have been approved.  If not provide detail list that were merged but not approved.  Output report at csv file

![ci](https://github.com/conventional-changelog/standard-version/workflows/ci/badge.svg)
[![version](https://img.shields.io/badge/version-1.x-yellow.svg)](https://semver.org)

## Table of Contents
* [General Info](#general-information)
* [Technologies Used](#technologies-used)
* [Features](#Features)
* [Assumptions](#Assumptions)
* [Usage](#usage)
* [Project Status](#project-status)

## General Information
- GitHub changelog action

## Technologies Used
- python script
- GitHub actions

## Features

* using python script to query GitHub api to get list of merged pull requests on target directory
* check if pull request has been approved
* if not approved, list the pull request that was merged but not approved

## Assumptions

* GitHub pat is required with read access to the repository

## Usage

* look at examples/change-audit.yml for usage

## Project Status
Project is: _in_progress_ 