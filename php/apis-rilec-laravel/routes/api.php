<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

use App\Http\Controllers\ApisHRMasterController;
use App\Http\Controllers\ApisOUController;
use App\Http\Controllers\ApisUserProfileController;
use App\Http\Controllers\ApisGroupAssignmentController;
use App\Http\Controllers\LDAPActionController;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
*/

Route::group(['middleware'=>'auth:api'], function(){
    /* Route::put('/replicate', 'ApisADController@update'); 
    Route::get('/replicate', 'ApisADController@list'); */
    Route::put('/hr/HRMaster/replicate', 'ApisHRMasterController@update');
    Route::get('/hr/HRMaster/replicate', 'ApisHRMasterController@list');
    /* Seznam uporabnikov v nekem trenutku */
    Route::get('/api/userprofile/', 'ApisUserProfileController@index');
    Route::get('/api/userprofile/{date}', 'ApisUserProfileController@index');
    /* Podatki o posamezniku v nekem trenutku */
    Route::get('/api/userprofile/{date}/{id}', 'ApisUserProfileController@show');
    /* Seznam org. enot v nekem trenutku */
    Route::get('/api/ou/{date}', [ApisOUController::class, 'index']);
    Route::get('/api/ou/', [ApisOUController::class, 'index']);
    /* Podrobnosti org. enote v nekem trenutku */
    Route::get('/api/ou/{date}/{id}', 'ApisOUController@show');
    /* Drevo org. enot v nekem trenutku */
    Route::get('/api/outree/{date}', 'ApisOUController@tree_index');
    /* Drevo org. enot z uporabniki v nekem trenutku */
    Route::get('/api/usertree/{date}', 'ApisUserProfileController@tree_index');
    /* Skupine, v katerih je v nekem trenutku posameznik - morda spada v userprofile */
    Route::get('/api/usermemberof/{date}/{id}', 'ApisUserProfileController@memberof');
    /* Pripadniki skupine v nekem trenutku - morda spada v podrobnosti enote */
    Route::get('/api/groupmembers/{date}/{id}', 'ApisOUController@members');
    /* Seznam kopiranj v AD */
    Route::get('/api/ldapaction/', 'GroupAssignmentController@index');
    /* Podrobnosti kopiranja v AD */
    Route::get('/api/ldapaction/{id}', 'GroupAssignmentController@id');
    /*
    Route::get('/user', function (Request $request) {
    return $request->user();
  }); */
});
