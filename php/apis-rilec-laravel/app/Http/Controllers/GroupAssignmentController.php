<?php

namespace App\Http\Controllers;

use App\GroupAssignment;
use Illuminate\Http\Request;

class GroupAssignmentController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index($date)
    {
        $gas = GroupAssignment::whereDate('valid_from', '<=', $date)
            ->whereDate('valid_to', '>=', $date)
            ->orderBy('changed_at')
            ->orderBy('updated_at')
            ->get();
        return $gas;
    }

}
