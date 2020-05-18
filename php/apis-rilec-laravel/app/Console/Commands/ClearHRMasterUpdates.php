<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Jobs\RemoveOldHRMasterUpdates;

class ClearHRMasterUpdates extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'apis:hrmclear';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Clear old HRMaster Entries (older than HRDATE_RETENTION_HOURS hours in .env)';

    /**
     * Create a new command instance.
     *
     * @return void
     */
    public function __construct()
    {
        parent::__construct();
    }

    /**
     * Execute the console command.
     *
     * @return mixed
     */
    public function handle()
    {
        RemoveOldHRMasterUpdates::dispatch();
    }
}
