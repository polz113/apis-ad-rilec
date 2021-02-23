<?php

namespace App\Http\Controllers;

use App\GroupAssignment;
use Illuminate\Http\Request;
use Carbon\Carbon;

class GroupAssignmentController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index($date = Null)
    {
        if (is_null($date)) {
            $date = Carbon::now();
        }
        $gas = GroupAssignment::whereDate('valid_from', '<=', $date)
            ->whereDate('valid_to', '>=', $date)
            ->orderBy('changed_at')
            ->orderBy('updated_at')
            ->get();
        return $gas;
    }

}
